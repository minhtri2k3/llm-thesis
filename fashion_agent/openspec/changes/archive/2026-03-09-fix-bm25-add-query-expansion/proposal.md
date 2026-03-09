## Why

Production BM25 index đang append `caption` vào `bm25_content`, trái ngược với notebook nghiên cứu gốc (`RAG_clothes_FashionCLIP2.ipynb`) nơi BM25 chỉ dùng `label + color`. Caption dài 30-40 từ gây noise cho keyword matching — khi user search "red shirt", BM25 sẽ match items mà caption mô tả "red stitching" dù item là áo xanh. Ngoài ra, notebook đã proven Query Expansion (Gemini expand synonyms) giúp tăng Recall ~20-30%, nhưng tính năng này chưa được port sang production.

## What Changes

- **Fix**: `indexing/build_index.py` — `compose_bm25_content()` chỉ giữ `label + color`, loại bỏ `caption`
- **Fix**: Rebuild BM25 index sau khi sửa (re-run `build_index.py build`)
- **Add**: Module `search/query_expansion.py` — Gemini-powered query expansion, sinh 3 synonym queries
- **Integrate**: `search/search_engine.py` — gọi `expand_query()` trước khi chạy BM25 + Vector retrieve, merge kết quả deduplicated

## Capabilities

### New Capabilities
- `query-expansion`: Gemini-powered query expansion trước khi search, sinh synonyms/variations (ví dụ: "navy shirt" → ["navy shirt", "dark blue shirt", "blue formal shirt"]), multi-query results được merge và dedup trước khi fusion

### Modified Capabilities
- `bm25-indexing`: BM25 content composition thay đổi từ `label + color + caption` → chỉ `label + color`, khớp với notebook nghiên cứu gốc

## Impact

- **Files sửa**: `indexing/build_index.py`, `search/search_engine.py`
- **Files tạo mới**: `search/query_expansion.py`
- **Data**: Qdrant payloads cần re-index để update `bm25_content` field (BM25 index in-memory sẽ tự rebuild khi API restart)
- **Dependencies**: Không thêm dependencies mới (đã có `google.generativeai` cho Gemini)
- **API**: Không breaking changes — search interface giữ nguyên
