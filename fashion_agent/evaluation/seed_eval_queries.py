"""Seed eval_queries table from eval_queries.json.

Usage (from fashion_agent/ directory):
    python -m evaluation.seed_eval_queries

Idempotent: skips rows with duplicate query_text (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from fashion_agent/ root
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    from agent.memory import _db_conn  # reuse shared pool

    json_path = Path(__file__).parent / "eval_queries.json"
    if not json_path.exists():
        print(f"ERROR: {json_path} not found")
        sys.exit(1)

    queries = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(queries)} queries from {json_path.name}")

    inserted = 0
    skipped = 0

    with _db_conn() as conn:
        with conn.cursor() as cur:
            for q in queries:
                cur.execute(
                    """
                    INSERT INTO eval_queries
                        (query_text, relevant_ids, category, difficulty, language)
                    VALUES (%s, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (query_text) DO NOTHING;
                    """,
                    (
                        q["query_text"],
                        json.dumps(q.get("relevant_ids", [])),
                        q.get("category", ""),
                        q.get("difficulty", "medium"),
                        q.get("language", "en"),
                    ),
                )
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
        conn.commit()

    print(f"Seeded {inserted} queries. {skipped} skipped (already exist).")


if __name__ == "__main__":
    main()
