## Why

Dự án Fashion Agent cần một RAG pipeline hoàn chỉnh để phục vụ tìm kiếm và tư vấn thời trang. Hiện tại chỉ có phần data ingestion + enrichment (captions/colors từ Gemini) đã hoàn thành trong `processing_data.py`. Cần xây dựng toàn bộ pipeline từ embedding → indexing → hybrid search → reranking → LLM synthesis → API endpoint, self-hosted trên Docker với Cloudflare Tunnel.

## What Changes

- **Thêm Docker Compose stack**: 4 containers (PostgreSQL, Qdrant, FastAPI, cloudflared) chạy trên M1 Mac 16GB
- **Sửa `processing_data.py`**: Bỏ Google Cloud SQL dependencies, kết nối Docker PostgreSQL local
- **Thêm embedding + indexing pipeline**: Encode images bằng Marqo-FashionSigLIP (768d), upsert vectors vào Qdrant
- **Thêm hybrid search pipeline**: BM25 + Vector retrieval → RRF Fusion → Soft Filter → BGE Reranker v2-m3
- **Thêm Agent logic**: Intent Classifier, Clarification Gate, Memory Agent, ReAct Loop, Gemini 2.5 Pro synthesis
- **Thêm API layer**: FastAPI REST endpoints + Gradio demo UI
- **Thêm Cloudflare Tunnel**: Public API qua zero-trust tunnel (không mở port)

## Capabilities

### New Capabilities
- `docker-infrastructure`: Docker Compose stack với PostgreSQL, Qdrant, FastAPI, cloudflared — self-hosted trên M1 Mac 16GB
- `embedding-indexing`: Encode fashion images bằng Marqo-FashionSigLIP (768d), upsert vào Qdrant collection, build BM25 index
- `hybrid-search`: Dual retrieval (BM25 + Vector ANN) → RRF Fusion (k=60) → Soft Relevance Filter (RapidFuzz) → BGE Reranker v2-m3 (top-6)
- `fashion-agent`: Intent Classifier, Clarification Gate, Memory Agent (PostgreSQL sessions), ReAct Loop, Gemini 2.5 Pro synthesis
- `api-layer`: FastAPI REST endpoints (POST /chat, GET /products, GET /images, GET /health) + Gradio UI mount

### Modified Capabilities
- `data-ingestion`: Sửa `processing_data.py` — bỏ GCP Cloud SQL dependencies (gcloud, ADC, cloud-sql-proxy), kết nối Docker PostgreSQL local qua env vars

## Impact

- **Code**: Thêm ~6 files Python mới (build_index.py, search_engine.py, reranker.py, fusion.py, fashion_agent.py, main.py), sửa 1 file (processing_data.py)
- **Infrastructure**: Thêm docker-compose.yml, Dockerfile, .env — cần Docker Desktop trên Mac
- **Dependencies**: Thêm `open-clip-torch`, `qdrant-client`, `fastapi`, `uvicorn`, `gradio`, `rapidfuzz`, `transformers`, `sentence-transformers`
- **External APIs**: Gemini API (giữ nguyên), HuggingFace Hub (download models)
- **Disk**: ~2GB thêm cho cached models (FashionSigLIP + BGE Reranker)
- **RAM**: ~5.1GB cho Docker services (trên tổng 16GB M1)
