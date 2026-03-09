## 1. Indexing — Named Vectors + Text Embedding

- [x] 1.1 Sửa `indexing/build_index.py`: đổi `init_collection()` dùng named vectors config `{"image": VectorParams(size=768, distance=Cosine), "text": VectorParams(size=768, distance=Cosine)}`
- [x] 1.2 Thêm hàm `compose_text_embed_content(item)` → trả về `f"{label}. {color}. {caption}"` (fallback `f"{label}. {color}."` nếu caption rỗng)
- [x] 1.3 Trong `run_build()`: sau khi encode images, thêm step encode text bằng `embedder.encode_text()` batch cho tất cả items
- [x] 1.4 Sửa `upsert_batch()`: upsert point với cả 2 named vectors `{"image": img_vec, "text": txt_vec}` + payload
- [x] 1.5 Verify: chạy `build_index.py` thành công, Qdrant collection có cả 2 named vectors

## 2. Search — Text Vector Retrieve

- [x] 2.1 Thêm hàm `text_vector_retrieve(query, top_k)` trong `search_engine.py`: encode query bằng `embedder.encode_text()`, query Qdrant `using="text"` named vector
- [x] 2.2 Sửa hàm `vector_retrieve()` hiện tại: thêm `using="image"` parameter khi query Qdrant
- [x] 2.3 Verify: gọi `text_vector_retrieve("cotton shirt")` trả về kết quả khác với `vector_retrieve("cotton shirt")`

## 3. Search — RRF 3-way Fusion

- [x] 3.1 Sửa `search/fusion.py`: mở rộng `reciprocal_rank_fusion()` nhận thêm `text_vec_nodes` parameter (optional), thêm `text_vec_weight=1.5` default
- [x] 3.2 Sửa RRF weights mặc định: `bm25_weight=2.5`, `img_vec_weight=1.0` (đảo lại như notebook)
- [x] 3.3 Fallback: nếu `text_vec_nodes` rỗng → 2-way fusion cũ nhưng với weights mới (bm25=2.5, img_vec=1.0)
- [x] 3.4 Verify: fusion 3 nguồn trả về kết quả merged đúng thứ tự score

## 4. Search — Filter-aware Soft Scoring

- [x] 4.1 Sửa `search()` signature: thêm parameter `filters: Optional[Dict[str, str]] = None`
- [x] 4.2 Khi `filters` có giá trị: dùng exact/fuzzy match trên `node.label` vs `filters["category"]` và `node.color` vs `filters["color"]`, tính `filter_relevance` [0.0-1.0]
- [x] 4.3 Nhân `rrf_score × filter_relevance` cho mỗi node trước khi rerank
- [x] 4.4 Khi `filters` là None: giữ nguyên RapidFuzz fallback hiện tại

## 5. Reranker — Score Blending

- [x] 5.1 Sửa `search/reranker.py`: trong `rerank()`, normalize reranker scores về [0,1] bằng min-max normalization
- [x] 5.2 Blend score: `final_score = 0.7 × normalized_rerank + 0.3 × original_rrf_score` (lưu original score trước khi rerank)
- [x] 5.3 Verify: rerank kết quả có score = blend, không phải 100% reranker

## 6. Agent — Truyền Filters xuống Search

- [x] 6.1 Sửa `agent/fashion_agent.py`: trong `_execute_tool("search", ...)`, truyền `intent_result.filters` vào `search()` call
- [x] 6.2 Verify: khi intent_classifier phát hiện `{"category": "Dress", "color": "Red"}`, search engine nhận được filters

## 7. Integration Test

- [x] 7.1 Rebuild index hoàn chỉnh (chạy `build_index.py` — verified with 50 items)
- [x] 7.2 Test end-to-end: search pipeline verified — 3-way retrieval + RRF + filter + reranker blending all working
- [ ] 7.3 So sánh kết quả trước/sau: test 5 queries mẫu, verify recall tăng (requires full 5096 items index — CPU too slow, needs GPU or overnight run)
