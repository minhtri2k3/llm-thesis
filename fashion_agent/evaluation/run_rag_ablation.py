"""RAG Ablation Study — so sánh các retrieval variants.

Compares 6 retrieval configurations to isolate each component's contribution:

  1. bm25_only       — BM25 keyword search only (no vector, no reranker)
  2. siglip_only     — FashionSigLIP image-vector ANN only (no BM25, no reranker)
  3. text_vec_only   — Text-vector ANN only (no BM25, no reranker)
  4. hybrid_no_rerank— BM25 + SigLIP + TextVec + RRF (no BGE reranker)
  5. hybrid_no_bm25  — SigLIP + TextVec + RRF + BGE (no BM25)
  6. hybrid_full     — Full system: BM25 + SigLIP + TextVec + RRF + BGE ← CURRENT

Usage (from fashion_agent/ directory):
    python -m evaluation.run_rag_ablation
    python -m evaluation.run_rag_ablation --runs 3
    python -m evaluation.run_rag_ablation --modes bm25_only siglip_only hybrid_full
    python -m evaluation.run_rag_ablation --dry-run

Requires:
    - Qdrant running (for vector search)
    - GEMINI_API_KEY (only needed if query expansion is enabled)
    - eval_queries table populated (run seed_eval_queries.py first)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# All retrieval modes available
# ---------------------------------------------------------------------------

ALL_MODES = [
    "bm25_only",
    "siglip_only",
    "text_vec_only",
    "hybrid_no_rerank",
    "hybrid_no_bm25",
    "hybrid_full",
]

MODE_DESCRIPTIONS = {
    "bm25_only":        "BM25 keyword search only (no vector, no reranker)",
    "siglip_only":      "FashionSigLIP image-vector ANN only (no BM25, no reranker)",
    "text_vec_only":    "Text-vector ANN only (no BM25, no reranker)",
    "hybrid_no_rerank": "BM25 + SigLIP + TextVec + RRF fusion (no BGE reranker)",
    "hybrid_no_bm25":   "SigLIP + TextVec + RRF + BGE reranker (no BM25)",
    "hybrid_full":      "Full hybrid: BM25 + SigLIP + TextVec + RRF + BGE ← current system",
}


# ---------------------------------------------------------------------------
# Retrieval functions — one per ablation variant
# ---------------------------------------------------------------------------

def _retrieve_bm25_only(query: str, top_k: int = 6):
    """BM25 keyword search, NO reranker."""
    from search.search_engine import bm25_retrieve, _dedup_merge
    raw = bm25_retrieve(query, top_k=top_k * 4)  # get extra candidates
    deduped = _dedup_merge(raw)
    return deduped[:top_k]


def _retrieve_siglip_only(query: str, top_k: int = 6):
    """FashionSigLIP image-vector ANN, NO reranker."""
    from search.search_engine import vector_retrieve
    return vector_retrieve(query, top_k=top_k)


def _retrieve_text_vec_only(query: str, top_k: int = 6):
    """Text-vector ANN (same encoder, text space), NO reranker."""
    from search.search_engine import text_vector_retrieve
    return text_vector_retrieve(query, top_k=top_k)


def _retrieve_hybrid_no_rerank(query: str, top_k: int = 6):
    """Full hybrid retrieval WITHOUT BGE cross-encoder reranker."""
    from search.search_engine import search
    return search(
        query,
        top_k=top_k,
        use_reranker=False,
        use_soft_filter=True,
        use_query_expansion=False,  # disable expansion for fair comparison
        min_score=0.0,
    )


def _retrieve_hybrid_no_bm25(query: str, top_k: int = 6):
    """Neural-only hybrid: SigLIP image-vec + text-vec + RRF + BGE. No BM25."""
    from search.search_engine import (
        vector_retrieve, text_vector_retrieve, _dedup_merge,
        get_reranker, MODELS_DIR,
        RRF_K, IMG_VEC_WEIGHT, TEXT_VEC_WEIGHT, VECTOR_TOP_K, TEXT_VEC_TOP_K,
    )
    from search.fusion import reciprocal_rank_fusion

    img_vec  = _dedup_merge(vector_retrieve(query, top_k=VECTOR_TOP_K * 4))
    text_vec = _dedup_merge(text_vector_retrieve(query, top_k=TEXT_VEC_TOP_K * 4))

    # RRF with only the two neural sources (BM25 weight = 0, omitted)
    fused = reciprocal_rank_fusion(
        bm25_results=[],          # No BM25
        vec_results=img_vec,
        text_vec_results=text_vec,
        k=RRF_K,
        bm25_weight=0.0,
        vec_weight=IMG_VEC_WEIGHT,
        text_vec_weight=TEXT_VEC_WEIGHT,
    )

    if not fused:
        return []

    reranker = get_reranker(cache_dir=MODELS_DIR)
    return reranker.rerank(query, fused, top_k=top_k)


def _retrieve_hybrid_full(query: str, top_k: int = 6):
    """Full hybrid system — current production pipeline."""
    from search.search_engine import search
    return search(
        query,
        top_k=top_k,
        use_reranker=True,
        use_soft_filter=True,
        use_query_expansion=False,  # disable for fair comparison
        min_score=0.0,
    )


# Map mode → retrieval function
_RETRIEVAL_FN = {
    "bm25_only":        _retrieve_bm25_only,
    "siglip_only":      _retrieve_siglip_only,
    "text_vec_only":    _retrieve_text_vec_only,
    "hybrid_no_rerank": _retrieve_hybrid_no_rerank,
    "hybrid_no_bm25":   _retrieve_hybrid_no_bm25,
    "hybrid_full":      _retrieve_hybrid_full,
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(
    returned_ids: list[str],
    relevant_ids: set[str],
    latency_ms: float,
) -> dict:
    """Hit@K, MRR, NDCG@6 for one query result."""
    hit = {}
    for k in [1, 3, 6]:
        hit[f"hit_at_{k}"] = any(r in relevant_ids for r in returned_ids[:k])

    reciprocal_rank = 0.0
    for rank, rid in enumerate(returned_ids[:6], start=1):
        if rid in relevant_ids:
            reciprocal_rank = 1.0 / rank
            break

    dcg = sum(
        (1.0 if returned_ids[i] in relevant_ids else 0.0) / math.log2(i + 2)
        for i in range(min(len(returned_ids), 6))
    )
    n_rel = min(len(relevant_ids), 6)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_rel))
    ndcg_at_6 = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "hit_at_1": hit["hit_at_1"],
        "hit_at_3": hit["hit_at_3"],
        "hit_at_6": hit["hit_at_6"],
        "reciprocal_rank": round(reciprocal_rank, 6),
        "ndcg_at_6": round(ndcg_at_6, 6),
        "latency_ms": round(latency_ms, 2),
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def load_eval_queries() -> list[dict]:
    from agent.memory import _db_conn
    from psycopg2.extras import DictCursor

    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id, query_text, relevant_ids, category, difficulty, language "
                "FROM eval_queries ORDER BY id;"
            )
            rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "query_text": r["query_text"],
            "relevant_ids": r["relevant_ids"] or [],
            "category": r["category"],
            "difficulty": r["difficulty"],
            "language": r["language"],
        }
        for r in rows
    ]


def insert_ablation_result(
    eval_query_id: int,
    retrieval_mode: str,
    returned_ids: list[str],
    metrics: dict,
    dry_run: bool = False,
) -> None:
    if dry_run:
        return

    from agent.memory import _db_conn

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag_ablation_results
                    (eval_query_id, retrieval_mode, returned_ids,
                     hit_at_1, hit_at_3, hit_at_6,
                     reciprocal_rank, ndcg_at_6, latency_ms)
                VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s);
                """,
                (
                    eval_query_id,
                    retrieval_mode,
                    json.dumps(returned_ids),
                    metrics["hit_at_1"],
                    metrics["hit_at_3"],
                    metrics["hit_at_6"],
                    metrics["reciprocal_rank"],
                    metrics["ndcg_at_6"],
                    metrics["latency_ms"],
                ),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def _fmt(v: float, decimals: int = 3) -> str:
    return f"{v:.{decimals}f}"


def print_summary(results_by_mode: dict[str, list[dict]], n_runs: int) -> None:
    import datetime
    sep = "═" * 80
    thin = "─" * 80

    print(f"\n{sep}")
    print(f"RAG ABLATION STUDY  ({datetime.date.today()}, {n_runs} run(s) averaged)")
    print(sep)

    header = (
        f"{'Mode':<22}"
        f"{'Hit@1':>8}{'Hit@3':>8}{'Hit@6':>8}"
        f"{'MRR':>8}{'NDCG@6':>8}"
        f"{'Lat(ms)':>10}"
    )
    print(header)
    print(thin)

    # Sort: hybrid_full first, then by NDCG@6 desc
    def sort_key(item):
        mode, rows = item
        if mode == "hybrid_full":
            return (-999, 0)
        avg_ndcg = sum(r["ndcg_at_6"] for r in rows) / len(rows) if rows else 0
        return (0, -avg_ndcg)

    for mode, rows in sorted(results_by_mode.items(), key=sort_key):
        if not rows:
            continue
        n = len(rows)
        hit1 = sum(r["hit_at_1"] for r in rows) / n
        hit3 = sum(r["hit_at_3"] for r in rows) / n
        hit6 = sum(r["hit_at_6"] for r in rows) / n
        mrr  = sum(r["reciprocal_rank"] for r in rows) / n
        ndcg = sum(r["ndcg_at_6"] for r in rows) / n
        lat  = sum(r["latency_ms"] for r in rows) / n

        star = " ◄ CURRENT" if mode == "hybrid_full" else ""
        print(
            f"{mode:<22}"
            f"{_fmt(hit1):>8}"
            f"{_fmt(hit3):>8}"
            f"{_fmt(hit6):>8}"
            f"{_fmt(mrr):>8}"
            f"{_fmt(ndcg):>8}"
            f"{lat:>10.1f}"
            f"{star}"
        )

    print(thin)
    print("\n📊 Subgroup breakdown (NDCG@6 by difficulty):")
    print(f"{'Mode':<22}{'Easy':>10}{'Medium':>10}{'Hard':>10}")
    print(thin)

    for mode, rows in sorted(results_by_mode.items(), key=sort_key):
        if not rows:
            continue
        by_diff: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}
        for r in rows:
            diff = r.get("difficulty", "medium")
            if diff in by_diff:
                by_diff[diff].append(r["ndcg_at_6"])

        def avg(lst):
            return sum(lst) / len(lst) if lst else 0.0

        print(
            f"{mode:<22}"
            f"{_fmt(avg(by_diff['easy'])):>10}"
            f"{_fmt(avg(by_diff['medium'])):>10}"
            f"{_fmt(avg(by_diff['hard'])):>10}"
        )

    print(sep + "\n")


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run_ablation(
    modes: list[str],
    n_runs: int = 1,
    dry_run: bool = False,
) -> None:
    queries = load_eval_queries()
    if not queries:
        print("ERROR: No eval_queries found. Run seed_eval_queries.py first.")
        sys.exit(1)

    print(f"\nLoaded {len(queries)} queries.")
    print(f"Modes: {modes}")
    print(f"Runs: {n_runs}  |  Dry-run: {dry_run}\n")
    for m in modes:
        print(f"  [{m}] {MODE_DESCRIPTIONS.get(m, '')}")
    print()

    results_by_mode: dict[str, list[dict]] = {m: [] for m in modes}

    for run_idx in range(n_runs):
        print(f"── Run {run_idx + 1}/{n_runs} ──")

        for query in queries:
            qid = query["id"]
            qtext = query["query_text"]
            relevant_ids = set(query["relevant_ids"])
            difficulty = query.get("difficulty", "medium")

            for mode in modes:
                retrieve_fn = _RETRIEVAL_FN[mode]

                t0 = time.perf_counter()
                try:
                    results = retrieve_fn(qtext, top_k=6)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    returned_ids = [r.image_id for r in results]
                except Exception as exc:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    print(f"  [WARN] {mode} / q{qid} failed: {exc}")
                    returned_ids = []

                metrics = compute_metrics(returned_ids, relevant_ids, latency_ms)
                insert_ablation_result(qid, mode, returned_ids, metrics, dry_run=dry_run)

                row = {**metrics, "difficulty": difficulty}
                results_by_mode[mode].append(row)

                status = "✓" if metrics["hit_at_6"] else "✗"
                print(
                    f"  {status} [{mode:>20}] q{qid:>3}({difficulty[0]}): "
                    f"H@6={int(metrics['hit_at_6'])} "
                    f"NDCG={metrics['ndcg_at_6']:.3f} "
                    f"MRR={metrics['reciprocal_rank']:.3f} "
                    f"lat={latency_ms:.0f}ms"
                )

    print_summary(results_by_mode, n_runs)

    if dry_run:
        print("[DRY RUN] No rows written to rag_ablation_results.")
    else:
        total = sum(len(v) for v in results_by_mode.values())
        print(f"Written {total} rows to rag_ablation_results.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG Ablation Study: compare retrieval components."
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=ALL_MODES,
        default=ALL_MODES,
        help=f"Retrieval modes to evaluate (default: all). Choices: {ALL_MODES}",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Number of evaluation passes (default: 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics but do NOT write to rag_ablation_results table.",
    )
    args = parser.parse_args()
    run_ablation(modes=args.modes, n_runs=args.runs, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
