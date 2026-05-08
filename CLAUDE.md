# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a thesis project ("Clothie / Fashion Agent") containing two co-deployed components:

- `fashion_agent/` — Python backend: FastAPI + Gradio API, RAG pipeline, LLM agent, indexing, preprocessing. **Most work happens here.**
- `clothie_web/` — Flutter web frontend (`flutter run -d chrome`, served at `:3000` via Docker, talks to the API at `:8000`).
- `qwen_local_rag/` — older local RAG experiment (legacy, rarely touched).
- `openspec/` and `fashion_agent/openspec/` — OpenSpec spec/change directories.
- `start.sh` (repo root) — one-command launcher that drives `docker compose` inside `fashion_agent/` and prints the Cloudflare tunnel URL.

## Common commands

All `docker compose` commands are run from `fashion_agent/` (compose file lives there). The `start.sh` wrapper handles `cd` for you.

```bash
# One-command start (DBs → wait healthy → build/run all → print public URL)
./start.sh
./start.sh --logs       # tail container logs
./start.sh --status     # docker compose ps
./start.sh --stop       # docker compose down

# From fashion_agent/
docker compose up -d postgres qdrant         # databases only (for local Python dev)
docker compose up -d --build fashion-api     # rebuild API after code changes
docker compose down                          # stop, KEEP data
docker compose down -v                       # stop and DELETE volumes (forces re-ingest!)

# Local Python dev (DBs in Docker, API on host)
cd fashion_agent
pip install -r requirements-docker.txt       # runtime deps
pip install -r requirements-dev.txt          # adds jupyter/pandas for analysis/
uv run python -m api.main                    # uv is the preferred runner in docs

# Offline ingestion (run inside fashion-api container or local venv)
python -m pre_processing.processing_data     # Kaggle → Postgres + Gemini caption/color
python -m indexing.build_index               # Postgres → SigLIP encode → Qdrant + BM25
python -m indexing.update_text_index         # refresh text vectors only (no re-encode of images)

# Tests
cd fashion_agent
uv run python test_search.py                 # quick search-pipeline smoke
uv run python test_chat.py                   # full agent pipeline smoke
uv run python test_selection_flow.py         # cart selection flow
pytest tests/ -k <name>                      # pytest suite under tests/ (orchestration, path2, language, …)
pytest tests/test_path2_image_search.py      # single test file
```

PATH 2 (image-to-image search) is gated behind `ENABLE_PATH2_IMAGE_SEARCH=true`. Toggle via env var when running compose.

## Architecture (the parts that span multiple files)

### Backend pipeline (a single chat call)

`POST /api/chat` → `agent.fashion_agent.chat()` (or `chat_stream()` for SSE) runs **direct routing**, not a ReAct loop. The README still describes a ReAct loop — that has been replaced. The current pipeline is:

1. **`agent/intent_classifier.py`** — one Gemini call returns `ClassifiedIntent` (intent, confidence, filters, refined_query) **and** 6 slots in `ExtractedSlots` (`category`, `color`, `fabric`, `fit`, `construction`, `aesthetic`).
2. **`agent/slot_completeness.py`** — slot merge across turns + readiness check. Slot accumulation per session uses `cachetools.TTLCache` (30-min TTL) keyed by `session_id` inside `fashion_agent.py` (`_session_accumulated_slots`, `_session_ranked_slots`, `_session_last_results`, `_session_pending_selection`). When the `category` slot changes, slots reset (new topic).
3. **`agent/clarification_gate.py`** — ranked-slot readiness gate. Decides whether to ask a templated clarification question (no LLM call) or proceed. `SEARCH_CONFIDENCE_THRESHOLD` env var (default `0.75`) gates pre-search.
4. **`_orchestrate()` / `_orchestrate_stream()` in `agent/fashion_agent.py`** — deterministic router that calls `search.search_engine.search()` directly and yields `ThinkingEvent`s for streaming UI.
5. **`search/search_engine.py`** — 7-stage hybrid search: query expansion (`search/query_expansion.py`, gated to short queries < 6 words) → BM25 (top-20) + image-vector ANN (top-20) + text-vector ANN (top-20) → dedup-merge → RRF (`search/fusion.py`, weights BM25=2.5, ImgVec=1.0, TxtVec=1.5, k=60) → RapidFuzz soft filter → BGE cross-encoder rerank (`search/reranker.py`, blend `0.7×reranker + 0.3×RRF`) → top-6.
6. **`_synthesize_response()` / `_synthesize_response_stream()`** — one Gemini call producing `{answer, styling_suggestion}`. Total per query: typically 1–2 LLM calls (intent + synthesis), plus 1 optional expansion call.

`agent/agentic_orchestrator.py` exists as scaffolding for Mode B (Gemini→GPT) and Mode C (GPT→Claude) tool-calling orchestration, but the live default is `_get_orchestration_mode()` returning `"direct"` with Gemini for both. Don't add tool-calling work assuming it's wired up — it's a stub path.

### Singleton models

`FashionEmbedder` (Marqo-FashionSigLIP, 768-d) and `BGEReranker` (BAAI/bge-reranker-v2-m3) are loaded once at first use and cached in module-level globals (`_embedder`, `get_reranker()`). The BM25 index is **rebuilt from Qdrant payloads on startup** — there is no on-disk BM25 file. If you change indexing or embedding code, restart the API container.

### Storage

- **Postgres** (`fashion-postgres`, port 5432, db `fashion_rag`, user `fashion_user`) — source of truth for items, enrichment, sessions, messages, query_history (JSONB), liked_items (JSONB), token usage logs. Schema is created at startup via `agent.memory.init_memory_tables()`.
- **Qdrant** (`fashion-qdrant`, port 6333) — collection `fashion_products` with two named vectors (`image_vector`, `text_vector`, both 768-d cosine). Payloads carry `image_id`, `label`, `color`, `caption`, `image_path`, `bm25_content`.
- **Volumes**: `fashion_agent_pgdata`, `fashion_agent_qdrant_data`. Backups exist at `fashion_agent/pgdata_backup.tar.gz` and `fashion_agent/qdrant_backup.tar.gz` (see `docs/handover.md` for restore steps).

### LLM client

`shared/llm.py` exposes `get_client(model_name)` returning a `LLMClient` Protocol with `.generate()` and `.stream()`. Currently Gemini-only (`google-generativeai`), even though the docker-compose accepts `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` for future modes. `GEMINI_API_KEY` is required at process start.

### Frontend ↔ backend contract

The Flutter app (`clothie_web/lib/services/api_service.dart`) calls `/api/chat`, `/api/products/{id}`, `/api/images/{filename}`, `/health`, plus PATH 2 image-upload endpoints when the flag is on. The Gradio UI mounted at `/` is a fallback chat UI used during development; production users hit the Flutter web app.

## Conventions and gotchas

- **README is partially stale.** It still describes the ReAct loop, `MAX_REACT_ITERATIONS=8`, and a pre-2.5 architecture. Trust the code in `agent/fashion_agent.py` (direct routing) over the README when they conflict.
- **Don't migrate `print()` to `logging` opportunistically.** Logging is mixed; agent code uses both. Stay consistent with the file you're editing.
- **Slot caches are in-memory**, scoped to a single API process. Multi-replica deployment would need to move them to Postgres or Redis.
- **`docker compose down -v` is destructive** — it wipes Postgres and Qdrant volumes, forcing the multi-hour re-ingest (`processing_data.py` + `build_index.py`). Use plain `docker compose down` to keep data.
- **Dataset images** are mounted read-only at `/app/dataset_images` in the container via the `DATASET_IMAGES_HOST_PATH` env var. `_convert_image_path()` in `api/main.py` rewrites host paths into container paths so the API can serve them.
- **Models cache.** SigLIP (~1 GB) and BGE (~1 GB) download to `./models/` on first run via `HF_HOME=/app/models`. Pre-download to skip the cold start.
- **Imports use package-style paths** (`from agent.memory import …`, `from search.search_engine import …`). Run scripts via `python -m <module>` from `fashion_agent/`, not as plain files.
- **PATH 2 is feature-flagged.** If you touch image-upload code, gate behavior on `ENABLE_PATH2_IMAGE_SEARCH` — never assume it's on.
