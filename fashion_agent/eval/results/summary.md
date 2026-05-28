# Ablation Evaluation Summary

N = 24 (query, picked_id) pairs

| Variant | Hit@1 | Hit@3 | Hit@6 | MRR | NDCG@6 | Avg Latency (ms) |
|---|---|---|---|---|---|---|
| BM25-only | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 22.2 |
| ImgVec-only | 0.042 | 0.292 | 0.542 | 0.215 | 0.287 | 789.2 |
| TxtVec-only | 0.167 | 0.333 | 0.583 | 0.289 | 0.359 | 103.0 |
| Full Hybrid + BGE | 0.333 | 0.5 | 0.75 | 0.455 | 0.521 | 2990.4 |

**Notes:** Single relevant item per query (user-observed cart-add). Variants run with `use_query_expansion=False` for fair single-signal compare. Top-K = 10 retrieved per variant; Hit@K computed on first K results.