# Spec: offline-eval-runner

## Overview

`evaluation/run_comparison.py` runs a fixed ground truth query set through both pipelines, measures retrieval metrics and efficiency, and writes results to `eval_results` in Postgres. Designed to run on the Mac Mini where Docker is running, or locally with a DB tunnel.

## CLI Interface

```bash
# Run both pipelines, 1 pass
python -m evaluation.run_comparison

# Run both pipelines, 3 passes (for mean ± std)
python -m evaluation.run_comparison --runs 3

# Run only one pipeline
python -m evaluation.run_comparison --mode direct
python -m evaluation.run_comparison --mode react

# Dry run (no DB writes, print metrics only)
python -m evaluation.run_comparison --dry-run
```

## Metric Definitions

```
hit_at_K    = 1 if any(id in relevant_ids for id in returned_ids[:K]) else 0
              K ∈ {1, 3, 6}

reciprocal_rank  = 1 / (rank of first relevant result)
                   = 0 if no relevant result in top-6

ndcg_at_6   = DCG@6 / IDCG@6
              DCG@6  = Σ rel_i / log2(i+2)  for i in 0..5
              IDCG@6 = max possible DCG for this query's relevant set
              rel_i  = 1 if returned_ids[i] in relevant_ids, else 0

latency_ms  = wall-clock time from chat() call to return, in milliseconds
              measured with time.perf_counter()

llm_call_count = 2 for Direct (classify + synthesize)
               = 2 + len(react_traces rows for this query) for ReAct

total_tokens = input_tokens + output_tokens + orchestrator_input_tokens + orchestrator_output_tokens
               from the log_token_usage() call
```

## Execution Logic

```python
for query in load_eval_queries():                    # from eval_queries table
    for mode in modes:                               # ['direct', 'react'] or subset
        session_id = create_eval_session(mode)       # throwaway session

        t0 = time.perf_counter()
        response = chat(query.query_text, session_id)
        latency_ms = (time.perf_counter() - t0) * 1000

        returned_ids = [p['image_id'] for p in response.products]
        relevant_ids = set(query.relevant_ids)

        metrics = compute_metrics(returned_ids, relevant_ids, latency_ms)
        # metrics: hit_at_1, hit_at_3, hit_at_6, reciprocal_rank, ndcg_at_6

        token_data = fetch_last_token_usage(session_id)
        insert_eval_result(query.id, mode, returned_ids, metrics, token_data)
```

## Summary Output (stdout)

```
══════════════════════════════════════════════════════════════════
OFFLINE EVALUATION RESULTS  (run 2026-05-24, 3 runs averaged)
══════════════════════════════════════════════════════════════════
Mode      Hit@1    Hit@3    Hit@6    MRR      NDCG@6   Latency(ms)  Tokens
────────  ──────   ──────   ──────   ──────   ──────   ───────────  ──────
direct    0.XXX    0.XXX    0.XXX    0.XXX    0.XXX    XXXX         XXXX
react     0.XXX    0.XXX    0.XXX    0.XXX    0.XXX    XXXX         XXXX
══════════════════════════════════════════════════════════════════
```

## Seeder: `evaluation/seed_eval_queries.py`

```bash
# Run once after DB migration to populate eval_queries:
python -m evaluation.seed_eval_queries
# Output: "Seeded 40 queries. 0 skipped (already exist)."
```

Reads from `evaluation/eval_queries.json`, inserts with `ON CONFLICT (query_text) DO NOTHING`.

## `evaluation/eval_queries.json` Schema

```json
[
  {
    "query_text": "white slim fit shirt for men",
    "relevant_ids": ["img_00142", "img_00891"],
    "category": "Shirt",
    "difficulty": "easy",
    "language": "en"
  },
  ...
]
```

**Annotation guideline:** `relevant_ids` contains image IDs that a human annotator would accept as a correct result for the query. Annotator should verify each ID exists in the Qdrant collection and that the product visually matches the query. Minimum 1 ID required; prefer 2–3.
