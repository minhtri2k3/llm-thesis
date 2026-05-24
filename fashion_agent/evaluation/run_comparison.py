"""Offline evaluation runner — Direct vs ReAct pipeline comparison.

Runs every query in eval_queries through both pipelines, computes retrieval
metrics (Hit@K, MRR, NDCG@6, latency, token cost), and writes results to
eval_results table in Postgres.

Usage (from fashion_agent/ directory):
    python -m evaluation.run_comparison
    python -m evaluation.run_comparison --runs 3
    python -m evaluation.run_comparison --mode direct
    python -m evaluation.run_comparison --mode react
    python -m evaluation.run_comparison --dry-run

Requirements:
    - Postgres (fashion_agent DB) must be accessible.
    - Qdrant must be running (for hybrid search inside fashion_agent.chat).
    - GEMINI_API_KEY must be set.
    - Run from the Mac Mini (or with a DB + Qdrant tunnel).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allow running from fashion_agent/ root
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_metrics(
    returned_ids: list[str],
    relevant_ids: set[str],
    latency_ms: float,
) -> dict:
    """Compute Hit@K, MRR, NDCG@6 for a single query result."""
    k_values = [1, 3, 6]
    hit = {}
    for k in k_values:
        top_k = returned_ids[:k]
        hit[f"hit_at_{k}"] = any(rid in relevant_ids for rid in top_k)

    # MRR: reciprocal rank of first relevant result (within top 6)
    reciprocal_rank = 0.0
    for rank, rid in enumerate(returned_ids[:6], start=1):
        if rid in relevant_ids:
            reciprocal_rank = 1.0 / rank
            break

    # NDCG@6
    dcg = 0.0
    for i, rid in enumerate(returned_ids[:6]):
        rel = 1.0 if rid in relevant_ids else 0.0
        dcg += rel / math.log2(i + 2)  # log2(rank+1), rank=i+1

    # IDCG: best possible for this query's relevant set
    n_relevant = min(len(relevant_ids), 6)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_relevant))
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
    """Load all rows from eval_queries table."""
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


def fetch_last_token_usage(session_id: str) -> dict:
    """Fetch the last llm_token_usage rows for a session and sum them up."""
    from agent.memory import _db_conn
    from psycopg2.extras import DictCursor

    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    SUM(input_tokens + output_tokens
                        + orchestrator_input_tokens + orchestrator_output_tokens) AS total_tokens,
                    SUM(llm_call_count) AS llm_call_count
                FROM llm_token_usage
                WHERE session_id = %s;
                """,
                (session_id,),
            )
            row = cur.fetchone()

    return {
        "total_tokens": int(row["total_tokens"] or 0) if row else 0,
        "llm_call_count": int(row["llm_call_count"] or 0) if row else 0,
    }


def count_react_tool_calls(session_id: str) -> int:
    """Count tool calls logged in react_traces for a session."""
    from agent.memory import _db_conn

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM react_traces WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()
    return int(row[0]) if row else 0


def insert_eval_result(
    eval_query_id: int,
    mode: str,
    returned_ids: list[str],
    metrics: dict,
    token_data: dict,
    dry_run: bool = False,
) -> None:
    """Insert one row into eval_results."""
    if dry_run:
        return

    from agent.memory import _db_conn

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO eval_results
                    (eval_query_id, orchestration_mode, returned_ids,
                     hit_at_1, hit_at_3, hit_at_6,
                     reciprocal_rank, ndcg_at_6,
                     latency_ms, llm_call_count, total_tokens)
                VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    eval_query_id,
                    mode,
                    json.dumps(returned_ids),
                    metrics["hit_at_1"],
                    metrics["hit_at_3"],
                    metrics["hit_at_6"],
                    metrics["reciprocal_rank"],
                    metrics["ndcg_at_6"],
                    metrics["latency_ms"],
                    token_data.get("llm_call_count", 0),
                    token_data.get("total_tokens", 0),
                ),
            )
        conn.commit()


def create_eval_session(mode: str) -> str:
    """Create a throwaway session tagged with the given mode."""
    from agent.memory import create_session
    return create_session(
        user_name=f"__eval_{mode}__",
        orchestration_mode=mode,
    )


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------


def _fmt(v: float, decimals: int = 3) -> str:
    return f"{v:.{decimals}f}"


def print_summary(
    results_by_mode: dict[str, list[dict]],
    run_date: str,
    n_runs: int,
) -> None:
    """Print a formatted comparison table to stdout."""
    sep = "═" * 72
    print(f"\n{sep}")
    print(f"OFFLINE EVALUATION RESULTS  (run {run_date}, {n_runs} run(s) averaged)")
    print(sep)
    header = f"{'Mode':<10}{'Hit@1':>8}{'Hit@3':>8}{'Hit@6':>8}{'MRR':>8}{'NDCG@6':>8}{'Lat(ms)':>11}{'Tokens':>9}"
    print(header)
    print("─" * 72)

    for mode, rows in sorted(results_by_mode.items()):
        if not rows:
            continue
        n = len(rows)
        hit1 = sum(r["hit_at_1"] for r in rows) / n
        hit3 = sum(r["hit_at_3"] for r in rows) / n
        hit6 = sum(r["hit_at_6"] for r in rows) / n
        mrr  = sum(r["reciprocal_rank"] for r in rows) / n
        ndcg = sum(r["ndcg_at_6"] for r in rows) / n
        lat  = sum(r["latency_ms"] for r in rows) / n
        tok  = sum(r["total_tokens"] for r in rows) / n
        print(
            f"{mode:<10}"
            f"{_fmt(hit1):>8}"
            f"{_fmt(hit3):>8}"
            f"{_fmt(hit6):>8}"
            f"{_fmt(mrr):>8}"
            f"{_fmt(ndcg):>8}"
            f"{lat:>11.1f}"
            f"{tok:>9.0f}"
        )
    print(sep + "\n")


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------


def run_evaluation(
    modes: list[str],
    n_runs: int = 1,
    dry_run: bool = False,
) -> None:
    """Run evaluation for the given modes N times."""
    import datetime

    # Import agents (lazy — avoids loading embedders until needed)
    agent_modules: dict = {}
    if "direct" in modes:
        from agent import fashion_agent
        agent_modules["direct"] = fashion_agent
    if "react" in modes:
        from agent import react_agent
        agent_modules["react"] = react_agent

    queries = load_eval_queries()
    if not queries:
        print("ERROR: No eval_queries found. Run seed_eval_queries.py first.")
        sys.exit(1)

    print(f"Loaded {len(queries)} queries. Modes: {modes}. Runs: {n_runs}. Dry-run: {dry_run}")

    run_date = datetime.date.today().isoformat()
    results_by_mode: dict[str, list[dict]] = {m: [] for m in modes}

    for run_idx in range(n_runs):
        print(f"\n── Run {run_idx + 1}/{n_runs} ──")
        for query in queries:
            qid = query["id"]
            qtext = query["query_text"]
            relevant_ids = set(query["relevant_ids"])

            for mode in modes:
                agent_mod = agent_modules[mode]
                session_id = create_eval_session(mode)

                t0 = time.perf_counter()
                try:
                    response = agent_mod.chat(qtext, session_id)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    returned_ids = [p.image_id for p in response.products]
                except Exception as exc:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    print(f"  [WARN] {mode} / q{qid} failed: {exc}")
                    returned_ids = []

                metrics = compute_metrics(returned_ids, relevant_ids, latency_ms)
                token_data = fetch_last_token_usage(session_id)

                # For ReAct, count actual tool calls for llm_call_count
                if mode == "react":
                    n_tools = count_react_tool_calls(session_id)
                    token_data["llm_call_count"] = 2 + n_tools  # classify + tools + synthesize

                insert_eval_result(qid, mode, returned_ids, metrics, token_data, dry_run=dry_run)

                result_row = {**metrics, **token_data}
                results_by_mode[mode].append(result_row)

                status = "✓" if metrics["hit_at_6"] else "✗"
                print(
                    f"  {status} [{mode}] q{qid}: "
                    f"Hit@6={int(metrics['hit_at_6'])} "
                    f"MRR={metrics['reciprocal_rank']:.3f} "
                    f"lat={latency_ms:.0f}ms "
                    f"tok={token_data.get('total_tokens', 0)}"
                )

    print_summary(results_by_mode, run_date, n_runs)

    if dry_run:
        print("[DRY RUN] No rows written to eval_results.")
    else:
        total_rows = sum(len(v) for v in results_by_mode.values())
        print(f"Written {total_rows} rows to eval_results.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline evaluation: Direct vs ReAct pipeline comparison."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Number of evaluation passes (default: 1). Use 3 for mean ± std reporting.",
    )
    parser.add_argument(
        "--mode",
        choices=["direct", "react", "both"],
        default="both",
        help="Which pipeline(s) to evaluate (default: both).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics but do NOT write to eval_results table.",
    )
    args = parser.parse_args()

    if args.mode == "both":
        modes = ["direct", "react"]
    else:
        modes = [args.mode]

    run_evaluation(modes=modes, n_runs=args.runs, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
