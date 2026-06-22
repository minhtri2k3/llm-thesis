# Ablation Evaluation Summary

N = 29 (query, picked_id) pairs

| Variant | Hit@1 | Hit@3 | Hit@6 | MRR | NDCG@6 | Avg Latency (ms) |
|---|---|---|---|---|---|---|
| BM25-only | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 47.0 |
| ImgVec-only | 0.034 | 0.276 | 0.552 | 0.212 | 0.289 | 1352.8 |
| TxtVec-only | 0.172 | 0.345 | 0.621 | 0.304 | 0.38 | 45.3 |
| Full Hybrid + BGE | 0.345 | 0.552 | 0.793 | 0.483 | 0.554 | 838.6 |

**Notes:** Single relevant item per query (user-observed cart-add). Variants run with `use_query_expansion=False` for fair single-signal compare. Top-K = 10 retrieved per variant; Hit@K computed on first K results.