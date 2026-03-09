## Context

Hệ thống Fashion RAG hiện tại có hybrid search pipeline: BM25 + Vector (Marqo-FashionSigLIP) → RRF Fusion → Soft Filter → BGE Rerank. Notebook nghiên cứu gốc (`RAG_clothes_FashionCLIP2.ipynb`) đã proven rằng BM25 chỉ nên index `label + color` (keyword ngắn gọn), còn caption dài phục vụ cross-encoder reranker. Production code (`compose_bm25_content`) đang sai — append cả caption vào BM25.

Query Expansion đã proven trên Colab: Gemini sinh 3 synonym queries, giúp Recall tăng ~20-30%. Feature này chưa có trong production.

## Goals / Non-Goals

**Goals:**
- Fix `compose_bm25_content()` để chỉ dùng `label + color`, align với notebook
- Port Query Expansion từ notebook vào production search pipeline
- Giữ nguyên search API interface (không breaking changes)

**Non-Goals:**
- Không thay đổi embedding model (vẫn Marqo-FashionSigLIP 768d)
- Không thêm Feedback System (phase sau)
- Không sửa ReAct agent logic
- Không fine-tune BM25 weights (BM25=1.0, Vec=2.5 giữ nguyên)

## Decisions

### 1. BM25 content = `label + color` only

**Lý do**: Notebook proven, caption 30-40 từ gây noise cho BM25 keyword matching. Caption vẫn được lưu trong Qdrant payload để reranker dùng.

**Thay đổi**: `compose_bm25_content()` loại bỏ `caption`:
```python
# Before
parts = [label, color, caption]  # 3 fields

# After
parts = [label, color]           # 2 fields only
```

**Re-indexing**: Cần chạy lại `build_index.py build` để update `bm25_content` trong Qdrant payloads. BM25 in-memory index sẽ tự rebuild khi API restart.

### 2. Query Expansion: Gemini-powered, max 3 queries

**Lý do**: Notebook Cell 28 `expand_query()` đã proven hiệu quả.

**Thiết kế**:
- Module riêng: `search/query_expansion.py`
- Input: raw query string
- Output: list of 3 expanded queries (bao gồm original)
- LLM: Gemini 2.5 Flash (đã có trong stack)
- Fallback: nếu Gemini fail → return `[original_query]`

### 3. Multi-query search strategy

**Lý do**: Mỗi expanded query chạy riêng BM25 + Vector → merge trước khi fusion.

**Approach**:
```
expand_query("navy shirt") → ["navy shirt", "dark blue shirt", "blue formal shirt"]
                                    │              │                │
                              BM25+Vec        BM25+Vec         BM25+Vec
                                    │              │                │
                                    └──── dedup by image_id ────────┘
                                              │
                                         RRF Fusion
                                              │
                                        Soft Filter
                                              │
                                        BGE Reranker
```

**Alternatives considered**:
- Concat expanded queries thành 1 query dài → rejected vì BM25 sẽ bị pha loãng
- Chỉ expand cho BM25 → rejected vì vector search cũng benefit từ synonyms

### 4. Query Expansion đặt trong search_engine, không phải agent

**Lý do**: Search engine là nơi logic retrieval sống. Agent chỉ gọi `search(query)` — expansion là implementation detail của search, không nên leak lên agent layer.

## Risks / Trade-offs

- **[Latency]** Query expansion thêm 1 Gemini API call (~200-500ms) → **Mitigation**: Cache expansion results, và chỉ expand khi query ngắn (< 6 từ). Query dài/complex đã đủ keywords.
- **[Re-indexing]** Sửa `compose_bm25_content` cần rebuild Qdrant payloads → **Mitigation**: `build_index.py build` idempotent, chỉ cần chạy 1 lần.
- **[Gemini quota]** Mỗi search call thêm 1 API call → **Mitigation**: Expansion prompt nhẹ (< 100 tokens), dùng Gemini Flash (cheap + fast).
