## 1. Fix BM25 Content Composition

- [x] 1.1 Update `compose_bm25_content()` in `indexing/build_index.py` — remove caption, keep only `label + color`
- [x] 1.2 Verify `compose_bm25_content()` handles edge cases: missing color, missing label, both missing

## 2. Re-index Qdrant

- [x] 2.1 Rebuild Docker services (`docker compose up -d postgres qdrant`)
- [x] 2.2 Run `build_index.py build` to re-index all items with new bm25_content
- [x] 2.3 Verify Qdrant payloads: `bm25_content` chỉ chứa `label. color.`, `caption` vẫn tồn tại riêng

## 3. Create Query Expansion Module

- [x] 3.1 Create `search/query_expansion.py` with `expand_query(query, max_expansions=3)` function
- [x] 3.2 Implement Gemini Flash prompt for fashion synonym generation
- [x] 3.3 Implement fallback logic: Gemini fail → return `[original_query]`
- [x] 3.4 Add short-query gate: chỉ expand khi query < 6 từ

## 4. Integrate Query Expansion vào Search Engine

- [x] 4.1 Update `search/search_engine.py` — import và gọi `expand_query()` trong `search()` function
- [x] 4.2 Implement multi-query retrieval: BM25 + Vector cho mỗi expanded query
- [x] 4.3 Implement dedup merge by `image_id` (giữ score cao nhất)
- [x] 4.4 Feed merged results vào RRF Fusion → Soft Filter → Reranker pipeline hiện tại

## 5. Integration Test

- [x] 5.1 Rebuild Docker image (`docker compose build fashion-api`)
- [x] 5.2 Start all services và verify API healthcheck
- [x] 5.3 Test BM25 fix: query "red shirt" — verify results không bị noise từ caption
- [x] 5.4 Test Query Expansion: query "navy shirt" — verify expanded queries trong logs
- [x] 5.5 Test fallback: set invalid Gemini key, verify search vẫn hoạt động với raw query
