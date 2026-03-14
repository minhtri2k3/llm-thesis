## 1. Configuration Constants Adjustment

- [ ] 1.1 In `fashion_agent/search/search_engine.py`, locate and edit `BM25_TOP_K` to 5.
- [ ] 1.2 In `fashion_agent/search/search_engine.py`, locate and edit `VECTOR_TOP_K` to 5.
- [ ] 1.3 In `fashion_agent/search/search_engine.py`, locate and edit `TEXT_VEC_TOP_K` to 5.
- [ ] 1.4 In `fashion_agent/search/search_engine.py`, locate and edit `RERANK_TOP_K` to 3.

## 2. Verification

- [ ] 2.1 Run a basic end-to-end functionality check or unit tests to ensure no index bound errors occur in the retrieval or reranking blocks with the newly reduced constants.
