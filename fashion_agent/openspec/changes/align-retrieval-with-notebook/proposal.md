## Why

Production retrieval pipeline thiếu **text embedding** so với notebook gốc (RAG_clothes_FashionCLIP2.ipynb). Notebook đạt độ chính xác retrieval cao nhờ 3 lớp bổ trợ: BM25 keyword, text vector (label+color+caption), và image vector. Production chỉ có 2 lớp (BM25 + image vector), bỏ mất text embedding khiến caption không tham gia vào retrieval stage — giảm recall cho các query mô tả chi tiết (chất liệu, kiểu dáng, phong cách).

Ngoài ra, RRF weights bị đảo ngược, reranker score blending bị bỏ, và soft filter không dùng LLM-extracted filters — tất cả đều khác notebook đã proven hiệu quả.

## What Changes

- **Thêm text embedding vào Qdrant**: Encode `label + color + caption` bằng SigLIP text encoder thành vector riêng biệt (named vector hoặc collection riêng), song song với image vector hiện có.
- **Thêm text_vector_retrieve()**: Hàm retrieve mới query trên text embeddings, trả về kết quả riêng tách khỏi image vector.
- **Sửa RRF weights**: Đảo lại BM25=2.5, Vec=1.0 cho phù hợp notebook đã proven.
- **Sửa reranker score blending**: Thay vì 100% rerank score, dùng `0.7×rerank + 0.3×original` như notebook.
- **Truyền intent filters vào search engine**: Chuyển `intent_result.filters` từ agent xuống `search()`, dùng cho soft filter scoring thay vì RapidFuzz thuần.

## Capabilities

### New Capabilities
- `text-vector-retrieval`: Thêm text embedding pipeline — encode text metadata (label+color+caption) thành SigLIP 768-d vector, lưu Qdrant named vector, và retrieve song song với image vector.

### Modified Capabilities
- `hybrid-search`: Sửa RRF weights (BM25=2.5, Vec=1.0), thêm text vector vào fusion, truyền filters vào soft filter.
- `reranking`: Sửa score blending 0.7×rerank + 0.3×original thay vì 100% rerank.

## Impact

- **indexing/build_index.py**: Thêm text vector encoding + upsert named vector vào Qdrant collection.
- **search/search_engine.py**: Thêm `text_vector_retrieve()`, sửa `search()` pipeline, sửa RRF weights, sửa soft filter.
- **search/reranker.py**: Sửa `BGEReranker.rerank()` thêm score blending.
- **search/fusion.py**: Có thể mở rộng `reciprocal_rank_fusion()` hỗ trợ 3 nguồn kết quả.
- **agent/fashion_agent.py**: Truyền `intent_result.filters` xuống search engine.
- **Qdrant collection schema**: Cần rebuild index (thêm named vector "text").
- **Không có breaking API changes** — Gradio UI và REST API giữ nguyên.
