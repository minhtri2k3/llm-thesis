# Self-Hosting CLI Guide

This document contains all the terminal commands needed to set up and initialize the Fashion Agent. Please execute these steps in order after you have launched **Docker Desktop** and finalized your `.env` file.

## Phase 1: Directory Preparation
Ensure the local folders for images and models exist with proper permissions.

```bash
cd /Users/tringuyen/llm-thesis
mkdir -p fashion_agent/images fashion_agent/models
chmod -R 777 fashion_agent/images fashion_agent/models
```

## Phase 2: Launch Application Stack
Build and start all services (PostgreSQL, Qdrant, FastAPI, Cloudflared).

```bash
cd /Users/tringuyen/llm-thesis/fashion_agent

# 1. Build the images
docker compose build

# 2. Start services in background
docker compose up -d

# 3. Check if all containers are healthy
docker compose ps
```

## Phase 3: Data Ingestion (PostgreSQL)
Import the metadata from `styles.csv` into the local database. This processes the first 5,000 items.

```bash
docker exec -it fashion-api python -m pre_processing.processing_data ingest-kaggle --limit 5000
```

## Phase 4: Data Enrichment (Gemini Flash)
Use Gemini 2.5 Flash to generate captions and detect colors for the images.
> [!NOTE]
> This script is resumable. If it stops, just run it again.

```bash
docker exec -it fashion-api python -m pre_processing.processing_data process --captions --colors --limit 5000
```

## Phase 5: Vector Indexing (Qdrant)
Initialize the vector collection and build the search index.

```bash
# 1. Initialize Qdrant collection
docker exec -it fashion-api python -m indexing.build_index init

# 2. Build vectors (Encode images and text)
docker exec -it fashion-api python -m indexing.build_index build --limit 5000
```

## Phase 6: Final Verification
Verify that the system is running and data is indexed.

```bash
# Check API health
curl http://localhost:8000/health

# Check Indexing stats
docker exec -it fashion-api python -m indexing.build_index status
```


``` This is for me .evn file ```

# ============================================================
# Fashion Agent RAG Pipeline — Environment Variables
# ============================================================

# ── PostgreSQL ──────────────────────────────────────────────
# Secure password for your local DB
PG_PASSWORD=21042024
PGDATABASE=fashion_rag
PGUSER=fashion_user

# ── Gemini API ──────────────────────────────────────────────
# REQUIRED: Get your key at https://aistudio.google.com/apikey
GEMINI_API_KEY=**REDACTED_GEMINI_API_KEY**

# ── Qdrant ──────────────────────────────────────────────────
# Authentication key for vector database (optional for local)
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mBlO4ak6kSsctjTUiu3th7YwtI_WrLswGCTdbNvYZuc

# ── Cloudflare Tunnel ───────────────────────────────────────
# Token for public HTTPS access (optional)
CF_TUNNEL_TOKEN=eyJhIjoiOGEzZDA5MDhhZDk3YzNhOWU5YzlhNTdhMTkwYjU5ZTAiLCJ0IjoiYmFjZDdhYmItOTE5NS00MjRkLWI4ZTUtMDAzYjc0YjY0ZDUyIiwicyI6Ik1HSTBZell6T1dFdE5tSXpNUzAwWlRneExXSmtPV1l0TVRRNU56VTRNMkZrT0dVeSJ9

# ── Paths ───────────────────────────────────────────────────
# Absolute path to your fashion product images on the host Mac
DATASET_IMAGES_HOST_PATH=/Users/tringuyen/llm-thesis/fashion_agent/images
