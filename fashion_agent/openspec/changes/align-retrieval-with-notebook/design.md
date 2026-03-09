## Context

Production fashion RAG pipeline (`fashion_agent/`) được refactor từ notebook `RAG_clothes_FashionCLIP2.ipynb`. Trong quá trình production-hóa, một số quyết định kiến trúc retrieval đã bị thay đổi so với notebook gốc — dẫn đến giảm retrieval accuracy.

**Hiện trạng production:**
- Qdrant chỉ lưu image vector (SigLIP 768-d encode ẢNH)
- BM25 search trên `label + color`
- RRF fusion: bm25_weight=1.0, vec_weight=2.5
- Reranker: 100% rerank score, không blend
- Soft filter: RapidFuzz fuzzy match, không dùng LLM filters

**Notebook gốc (proven accuracy cao):**
- Qdrant lưu CẢ text vector (FashionCLIP encode `label+color+caption`) VÀ image vector
- BM25 search trên `label + color`
- RRF fusion: bm25_weight=2.5, vec_weight=1.0
- Reranker: 0.7×rerank + 0.3×original
- Soft filter: LLM-extracted filters × relevance scoring

## Goals / Non-Goals

**Goals:**
- Khôi phục retrieval architecture 3 lớp của notebook (BM25 + text vector + image vector)
- Đồng bộ RRF weights, reranker blending, và filter scoring với notebook
- Giữ nguyên API interface (Gradio UI + REST không thay đổi)
- Backward-compatible: có thể rebuild index mà không ảnh hưởng data

**Non-Goals:**
- Thay đổi embedding model (giữ SigLIP, không quay lại FashionCLIP)
- Thêm Image Node retrieval riêng biệt (notebook trả TextNode + ImageNode riêng, production giữ single list — đơn giản hơn mà vẫn đủ tốt)
- Thay đổi preprocessing pipeline (caption/color generation giữ nguyên Gemini)
- Tối ưu performance (tập trung accuracy trước)

## Decisions

### 1. Named Vectors trong Qdrant (thay vì collection riêng)

**Chọn**: Qdrant Named Vectors — 1 collection, 2 named vectors: `"image"` (768-d) và `"text"` (768-d).

**Thay vì**: 2 collections riêng biệt (`fashion_images`, `fashion_texts`).

**Lý do**: Named vectors giữ payload chung, avoid data duplication, và Qdrant hỗ trợ tốt multi-vector search. Notebook dùng LlamaIndex nên tự quản lý 2 loại node, nhưng thuần Qdrant thì named vectors là idiomatic hơn.

### 2. Text Embedding Content = `label + ". " + color + ". " + caption`

**Chọn**: Concat `label.color.caption` thành 1 string, encode qua SigLIP text encoder (cùng model đang dùng cho query encoding).

**Lý do**: Notebook dùng `excluded_embed_metadata_keys` để loại `image_id, image_path, category, color` khỏi embedding, chỉ giữ lại `full_description` (caption) + text content (`label.color.`). Production sẽ replicate chính xác logic này.

### 3. RRF 3-way Fusion

**Chọn**: Mở rộng `reciprocal_rank_fusion()` nhận 3 danh sách: BM25, text_vec, image_vec.

**Công thức**:
```
rrf_score = bm25_weight × 1/(k + rank_bm25 + 1)
          + text_vec_weight × 1/(k + rank_text + 1)  
          + img_vec_weight × 1/(k + rank_img + 1)
```

**Weights**: `bm25=2.5, text_vec=1.5, img_vec=1.0` — ưu tiên keyword > text semantic > visual semantic. Notebook dùng bm25=2.5 cho text fusion, vec=1.0 cho image riêng. Production gộp thành 1 fusion step nhưng giữ tỷ lệ tương đương.

### 4. Score Blending cho Reranker

**Chọn**: `final_score = 0.7 × reranker_score + 0.3 × rrf_score` (giống notebook).

**Lý do**: RRF score chứa thông tin rank position từ 3 retriever. Bỏ hoàn toàn (100% rerank) mất context này. Blending 70/30 giữ cả hai signals.

### 5. Filter-aware Soft Scoring (Hybrid)

**Chọn**: Kết hợp RapidFuzz (nhanh) + intent filters (chính xác).

**Logic**:
- `search()` nhận thêm parameter `filters: dict` (từ `intent_classifier`)
- Nếu có filters → dùng exact/fuzzy match trên `category` và `color` metadata
- Score = `rrf_score × filter_relevance` (nhân hệ số, giống notebook)
- Nếu không có filters → giữ nguyên RapidFuzz fallback

## Risks / Trade-offs

**[Qdrant rebuild bắt buộc]** → Phải xóa collection cũ và rebuild toàn bộ. Mitigation: Script `build_index.py` đã idempotent, chỉ cần chạy lại với `--rebuild` flag.

**[Tăng latency indexing]** → Thêm text encoding step. Mitigation: Text encoding nhanh hơn image encoding nhiều lần (batch text vs individual image). Tăng ~10-15% thời gian build.

**[Tăng memory Qdrant]** → Thêm 768-d vector per point (~6KB/point). Mitigation: Với ~5000 items, chỉ thêm ~30MB — không đáng kể.

**[RRF 3-way weights cần tune]** → Chưa có benchmark chính xác cho 3-way fusion. Mitigation: Bắt đầu với weights gần notebook (2.5/1.5/1.0), test thủ công, có thể điều chỉnh sau.

**[Rollback]** → Nếu accuracy giảm, có thể revert code changes và rebuild index cũ (image-only). Data trong PostgreSQL không bị ảnh hưởng.
