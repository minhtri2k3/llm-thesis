"""Offline ablation evaluation: 4 retrieval variants × N user-observed cart-adds.

Variants:
    1. BM25-only
    2. ImgVec-only (FashionSigLIP image vector ANN)
    3. TxtVec-only (FashionSigLIP text vector ANN)
    4. Full Hybrid + BGE rerank (production pipeline)

Metrics per variant:
    Hit@1, Hit@3, Hit@6, MRR@10, NDCG@6 (binary relevance)

Ground truth:
    (query, picked_id) pairs harvested from selected_items + product_impressions.
    Single relevant item per query (the cart-added product).

Usage (from fashion_agent/):
    uv run python -m eval.ablation
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

# Local imports — script must run from fashion_agent/ so that `search`
# and `eval` packages are importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search.search_engine import (  # noqa: E402
    bm25_retrieve,
    vector_retrieve,
    text_vector_retrieve,
    search as full_hybrid_search,
)
from eval.manual_recovery import MANUAL_CASES  # noqa: E402


TOP_K_EVAL = 10  # retrieve top-10 from every variant so we can compute MRR / NDCG@6


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

def fetch_recovered_cases() -> list[dict]:
    """Pull 19 (query, picked_id) pairs recovered via impressions join."""
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "fashion_rag"),
        user=os.getenv("PGUSER", "fashion_user"),
        password=os.getenv("PGPASSWORD", ""),
    )
    sql = """
    SELECT
      s.session_id,
      s.image_id AS picked_id,
      s.position AS pick_position,
      s.selected_at,
      (
        SELECT i.search_query
        FROM product_impressions i
        WHERE i.session_id = s.session_id
          AND i.image_id = s.image_id
          AND i.shown_at <= s.selected_at
        ORDER BY i.shown_at DESC
        LIMIT 1
      ) AS query
    FROM selected_items s
    WHERE s.path_mode = 'path1'
    """
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    conn.close()
    return [
        {
            "session_id": r["session_id"],
            "picked_id": r["picked_id"],
            "query": r["query"],
            "pick_position": r["pick_position"],
            "source": "impressions",
        }
        for r in rows
        if r["query"] is not None
    ]


def build_eval_dataset() -> list[dict]:
    recovered = fetch_recovered_cases()
    manual = [
        {
            "session_id": c["session_id"],
            "picked_id": c["picked_id"],
            "query": c["query"],
            "pick_position": c["pick_position"],
            "source": "manual_from_history",
        }
        for c in MANUAL_CASES
    ]
    return recovered + manual


# ---------------------------------------------------------------------------
# Variant runners — all return list[image_id] sorted by relevance, length up to TOP_K_EVAL
# ---------------------------------------------------------------------------

def run_bm25_only(query: str) -> list[str]:
    nodes = bm25_retrieve(query, top_k=TOP_K_EVAL)
    return [n.image_id for n in nodes]


def run_img_only(query: str) -> list[str]:
    nodes = vector_retrieve(query, top_k=TOP_K_EVAL)
    return [n.image_id for n in nodes]


def run_text_only(query: str) -> list[str]:
    nodes = text_vector_retrieve(query, top_k=TOP_K_EVAL)
    return [n.image_id for n in nodes]


def run_full_hybrid(query: str) -> list[str]:
    nodes = full_hybrid_search(
        query=query,
        top_k=TOP_K_EVAL,
        use_reranker=True,
        use_soft_filter=True,
        use_query_expansion=False,  # OFF — fair compare with single-signal variants
        filters=None,
        min_score=0.0,  # disable threshold to preserve ranks for MRR/NDCG
        min_results=TOP_K_EVAL,
    )
    return [n.image_id for n in nodes]


VARIANTS = [
    ("BM25-only", run_bm25_only),
    ("ImgVec-only", run_img_only),
    ("TxtVec-only", run_text_only),
    ("Full Hybrid + BGE", run_full_hybrid),
]


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def rank_of(picked_id: str, results: list[str]) -> int:
    """Return 1-indexed rank of picked_id in results, or 0 if not present."""
    for i, rid in enumerate(results):
        if rid == picked_id:
            return i + 1
    return 0


def hit_at_k(rank: int, k: int) -> int:
    return 1 if 0 < rank <= k else 0


def reciprocal_rank(rank: int) -> float:
    return 1.0 / rank if rank > 0 else 0.0


def ndcg_at_k(rank: int, k: int) -> float:
    """Binary relevance, single relevant item per query.
    NDCG@k = 1 / log2(rank+1) if rank ≤ k else 0; IDCG = 1.
    """
    if 0 < rank <= k:
        return 1.0 / math.log2(rank + 1)
    return 0.0


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> None:
    eval_set = build_eval_dataset()
    print(f"Eval dataset size: {len(eval_set)} (query, picked_id) pairs")
    print(f"  - From impressions: {sum(1 for c in eval_set if c['source'] == 'impressions')}")
    print(f"  - Manual recovery:  {sum(1 for c in eval_set if c['source'] == 'manual_from_history')}")
    print()

    # Save dataset for reference
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "eval_dataset.json").write_text(json.dumps(eval_set, indent=2, default=str))

    # ── Run all variants ────────────────────────────────────────────────
    per_query_rows: list[dict] = []  # one row per (query, variant)
    aggregate: dict[str, dict] = {}  # variant_name → metric dict

    for variant_name, runner in VARIANTS:
        print(f"▶ Running variant: {variant_name}")
        hit1 = hit3 = hit6 = 0
        mrr_sum = 0.0
        ndcg6_sum = 0.0
        latencies = []
        t_variant_start = time.time()

        for i, case in enumerate(eval_set, 1):
            q = case["query"]
            picked = case["picked_id"]
            t0 = time.time()
            try:
                results = runner(q)
            except Exception as exc:
                print(f"    [{i:02d}] ERROR on query={q!r}: {exc}")
                results = []
            dt = time.time() - t0
            latencies.append(dt)
            rank = rank_of(picked, results)
            h1 = hit_at_k(rank, 1)
            h3 = hit_at_k(rank, 3)
            h6 = hit_at_k(rank, 6)
            rr = reciprocal_rank(rank)
            nd = ndcg_at_k(rank, 6)
            hit1 += h1
            hit3 += h3
            hit6 += h6
            mrr_sum += rr
            ndcg6_sum += nd
            per_query_rows.append({
                "variant": variant_name,
                "query": q,
                "picked_id": picked,
                "rank": rank,
                "hit@1": h1,
                "hit@3": h3,
                "hit@6": h6,
                "rr": round(rr, 4),
                "ndcg@6": round(nd, 4),
                "latency_s": round(dt, 4),
                "source": case["source"],
            })

        n = len(eval_set)
        aggregate[variant_name] = {
            "Hit@1": round(hit1 / n, 3),
            "Hit@3": round(hit3 / n, 3),
            "Hit@6": round(hit6 / n, 3),
            "MRR": round(mrr_sum / n, 3),
            "NDCG@6": round(ndcg6_sum / n, 3),
            "AvgLatency_ms": round(1000 * sum(latencies) / n, 1),
            "VariantTotal_s": round(time.time() - t_variant_start, 1),
        }
        print(f"    Hit@1={hit1}/{n}  Hit@3={hit3}/{n}  Hit@6={hit6}/{n}  MRR={mrr_sum/n:.3f}  NDCG@6={ndcg6_sum/n:.3f}")
        print()

    # ── Write outputs ───────────────────────────────────────────────────
    # 1) per_query CSV
    per_query_csv = out_dir / "per_query.csv"
    with per_query_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_query_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_query_rows)

    # 2) summary CSV
    summary_csv = out_dir / "summary.csv"
    with summary_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "Hit@1", "Hit@3", "Hit@6", "MRR", "NDCG@6", "AvgLatency_ms"])
        for v_name, _ in VARIANTS:
            m = aggregate[v_name]
            writer.writerow([v_name, m["Hit@1"], m["Hit@3"], m["Hit@6"], m["MRR"], m["NDCG@6"], m["AvgLatency_ms"]])

    # 3) markdown summary table
    md_lines = ["# Ablation Evaluation Summary", "", f"N = {len(eval_set)} (query, picked_id) pairs", "",
                "| Variant | Hit@1 | Hit@3 | Hit@6 | MRR | NDCG@6 | Avg Latency (ms) |",
                "|---|---|---|---|---|---|---|"]
    for v_name, _ in VARIANTS:
        m = aggregate[v_name]
        md_lines.append(
            f"| {v_name} | {m['Hit@1']} | {m['Hit@3']} | {m['Hit@6']} | {m['MRR']} | {m['NDCG@6']} | {m['AvgLatency_ms']} |"
        )
    md_lines.append("")
    md_lines.append("**Notes:** Single relevant item per query (user-observed cart-add). "
                    "Variants run with `use_query_expansion=False` for fair single-signal compare. "
                    "Top-K = 10 retrieved per variant; Hit@K computed on first K results.")
    (out_dir / "summary.md").write_text("\n".join(md_lines))

    # 4) matplotlib chart
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        variants_x = [v for v, _ in VARIANTS]
        hit1 = [aggregate[v]["Hit@1"] for v in variants_x]
        hit3 = [aggregate[v]["Hit@3"] for v in variants_x]
        hit6 = [aggregate[v]["Hit@6"] for v in variants_x]
        mrr = [aggregate[v]["MRR"] for v in variants_x]

        x_pos = list(range(len(variants_x)))
        width = 0.2
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.bar([x - 1.5 * width for x in x_pos], hit1, width, label="Hit@1", color="#3B82F6")
        ax.bar([x - 0.5 * width for x in x_pos], hit3, width, label="Hit@3", color="#10B981")
        ax.bar([x + 0.5 * width for x in x_pos], hit6, width, label="Hit@6", color="#A78BFA")
        ax.bar([x + 1.5 * width for x in x_pos], mrr, width, label="MRR", color="#F59E0B")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(variants_x, rotation=0, fontsize=10)
        ax.set_ylabel("Score", fontsize=11)
        ax.set_title(f"Retrieval Ablation — N={len(eval_set)} user-observed picks", fontsize=13)
        ax.legend(loc="upper left")
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        for variant_idx, v in enumerate(variants_x):
            for metric_idx, (label, val) in enumerate(zip(["Hit@1","Hit@3","Hit@6","MRR"], [hit1[variant_idx], hit3[variant_idx], hit6[variant_idx], mrr[variant_idx]])):
                ax.text(variant_idx + (metric_idx - 1.5) * width, val + 0.02, f"{val:.2f}",
                        ha="center", fontsize=8)
        fig.tight_layout()
        chart_path = out_dir / "ablation_chart.png"
        fig.savefig(chart_path, dpi=150)
        print(f"Chart saved: {chart_path}")
    except ImportError:
        print("matplotlib not available — skipping chart")

    print()
    print("─" * 70)
    print("FINAL SUMMARY")
    print("─" * 70)
    print(f"{'Variant':<22} {'Hit@1':>7} {'Hit@3':>7} {'Hit@6':>7} {'MRR':>7} {'NDCG@6':>8} {'Lat(ms)':>9}")
    for v_name, _ in VARIANTS:
        m = aggregate[v_name]
        print(f"{v_name:<22} {m['Hit@1']:>7} {m['Hit@3']:>7} {m['Hit@6']:>7} {m['MRR']:>7} {m['NDCG@6']:>8} {m['AvgLatency_ms']:>9}")
    print()
    print(f"Outputs in: {out_dir}")


if __name__ == "__main__":
    main()
