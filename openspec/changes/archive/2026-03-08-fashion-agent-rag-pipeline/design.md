## Context

Dự án Fashion Agent xây dựng hệ thống RAG tìm kiếm và tư vấn thời trang. Hiện trạng:
- `processing_data.py` đã hoàn thành: ingest Kaggle data, Gemini caption/color enrichment, PostgreSQL schema → nhưng kết nối Google Cloud SQL qua proxy
- Chưa có embedding, vector indexing, search pipeline, agent logic, hay API layer
- Target: self-host toàn bộ trên Mac M1 16GB RAM, expose qua Cloudflare Tunnel
- Report gốc (Faculty thesis) dùng FashionCLIP 2.0 — upgrade lên Marqo-FashionSigLIP (+57% accuracy)

## Goals / Non-Goals

**Goals:**
- Xây dựng end-to-end RAG pipeline: data enrichment → embedding → indexing → hybrid search → reranking → LLM synthesis
- Self-host trên Docker Compose (M1 16GB): PostgreSQL + Qdrant + FastAPI + cloudflared
- Public API qua Cloudflare Tunnel (zero-trust, free tier)
- Hybrid retrieval: BM25 + Vector → RRF Fusion → Soft Filter → BGE Reranker → top-6 results
- Agent logic: Intent classification, clarification, memory, ReAct loop, Gemini synthesis
- RAM budget ≤ 8.8GB cho tất cả services
- Query latency ≤ 3s end-to-end

**Non-Goals:**
- Triển khai lên cloud (GCP, AWS) — chỉ self-host local
- Training custom embedding model — dùng pretrained Marqo-FashionSigLIP
- Real-time data updates — batch processing (chạy build_index.py khi cần)
- Multi-user authentication — single-user/demo mode cho thesis
- Mobile app — chỉ web UI qua Gradio

## Decisions

### 1. Embedding Model: Marqo-FashionSigLIP (768d)
**Choice**: `Marqo/marqo-fashionSigLIP` (ViT-B-16-SigLIP, ~400M params, 768d output)

**Alternatives considered**:
| Option | Dimensions | Fashion Accuracy | RAM | Why not |
|---|---|---|---|---|
| FashionCLIP 2.0 (Report gốc) | 512 | baseline | 600MB | +57% improvement available |
| Marqo-FashionCLIP | 512 | +40% | 600MB | SigLIP variant is strictly better |
| SigLIP2 (generic) | 768 | +30% | 1.2GB | Not fashion-tuned |
| Jina-CLIP-v2 | 1024 | ~1.2x | 2.5GB | Too heavy for 16GB, generic |

**Rationale**: Best fashion-domain accuracy (+57% vs Report baseline), fits in M1 16GB budget, drop-in replacement (thay 1 dòng model name). Thesis value: clear improvement to cite.

### 2. Reranker: bge-reranker-v2-m3 (~570M params)
**Choice**: `BAAI/bge-reranker-v2-m3`

**Alternatives considered**:
| Option | Params | Latency (CPU, 20 docs) | Accuracy | Why not |
|---|---|---|---|---|
| bge-reranker-v2-gemma | 2.5B | 2-5s ⚠️ | ★★★★★ | Too slow on M1 CPU |
| Jina Reranker v2 | 278M | 150-300ms | ★★★★ | Slightly less accurate |
| FlashRank | 22M | 30-50ms | ★★★ | Too weak for thesis |
| Cohere Rerank 4 | API | 100ms | ★★★★★ | External API dependency |

**Rationale**: Giữ nguyên từ Report gốc, không cần justify thêm. Multilingual, proven, ~200-400ms trên M1 CPU.

### 3. Database: Docker PostgreSQL local (thay Cloud SQL)
**Choice**: `postgres:16-alpine` container, internal Docker network only

**Rationale**: Bỏ toàn bộ GCP dependencies (gcloud, ADC, cloud-sql-proxy). Connection code giữ nguyên (psycopg2 + env vars). Schema không đổi. Doctor command đơn giản hóa.

### 4. Vector Store: Qdrant (Docker local)
**Choice**: `qdrant/qdrant:latest` container

**Alternatives considered**:
| Option | Why not |
|---|---|
| ChromaDB | Thiếu production features, no gRPC |
| Milvus | Quá nặng cho single-node |
| Weaviate | Overkill, phức tạp config |
| pgvector (PostgreSQL extension) | Chậm hơn Qdrant HNSW cho ANN |

**Rationale**: Qdrant lightweight, HNSW index built-in, REST + gRPC API, Docker image nhỏ, persistence qua volume. Phù hợp nhất cho self-host đơn node.

### 5. API Layer: FastAPI + Gradio
**Choice**: FastAPI cho REST endpoints, Gradio mount tại `/` cho demo UI

**Rationale**: FastAPI async performance, auto OpenAPI docs. Gradio = zero-effort UI cho thesis demo. Cả hai chạy trong 1 container.

### 6. Networking: Cloudflare Tunnel
**Choice**: `cloudflare/cloudflared` container, outbound-only tunnel

**Rationale**: Không mở port trên router, không cần static IP, auto SSL, DDoS protection, free tier (50 users). Phù hợp cho self-host qua NAT.

### 7. Search Pipeline: Hybrid BM25 + Vector → RRF → Soft Filter → Rerank
**Choice**: Follow Report architecture

```
BM25 (top-20) + Vector ANN (top-20)
    → RRF Fusion (k=60, vec_weight=2.5)
    → Soft Filter (RapidFuzz, color/category)
    → BGE Reranker (top-6)
    → Gemini Synthesis
```

**Rationale**: Report đã validate architecture. Upgrade embedding model (SigLIP) cải thiện vector retrieval quality. Giữ nguyên fusion/filter/rerank logic.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| M1 16GB RAM pressure khi load cả 2 models | Medium | FP16 inference, lazy model loading, ~7.2GB headroom |
| Mac tắt/restart → API downtime | High | Docker restart policy `unless-stopped`, systemd/launchd auto-start |
| Gemini API cost tăng khi nhiều queries | Low | Cache frequent responses, rate limit API |
| Qdrant data loss khi Docker volume bị xóa | High | Named volumes + backup script (pg_dump + qdrant snapshot) |
| Cloudflare free tier giới hạn | Low | 50 concurrent users đủ cho thesis demo |
| FashionSigLIP cold start chậm (~10s load model) | Low | Preload model khi container start, keep warm |
| BGE Reranker chậm trên CPU (>400ms nếu nhiều docs) | Medium | Limit rerank input to 20 docs |
