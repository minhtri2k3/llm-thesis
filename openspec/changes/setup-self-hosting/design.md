# Design: Self-Hosting Configuration

## Architecture
The system follows a containerized 4-service architecture managed by `docker-compose.yml`.

### 1. Environment Configuration (`.env`)
The system requires specific environment variables to bridge containers:
- `PG_PASSWORD`: Secure password for the DB.
- `GEMINI_API_KEY`: Authentication for Google Gemini.
- `PGDATABASE`: Database name (default `fashion_rag`).
- `PGUSER`: Database user (default `fashion_user`).

### 2. Checkpointing & Resilience
The data pipeline is designed to be **idempotent**:
- **PostgreSQL Enrichment**: The script queries for items where `caption IS NULL`. Once an item is enriched, the `caption` field is updated. If the script restarts, it automatically skips already processed items.
- **Qdrant Indexing**: The indexing script scrolls through the existing Qdrant collection IDs before starting. It only encodes and upserts items that are missing from the vector store.
- **Batching**: Data is processed in batches (default: 32) to minimize impact on system resources and provide frequent save points.

### 3. Multi-Stage Deployment
- **Phase 1: DB & Vector Store**: Start persistent services first.
- **Phase 2: API & UI**: Build the application container from the `Dockerfile`.
- **Phase 3: Data Ingestion**: Import CSV and Image paths into PostgreSQL.
- **Phase 4: Data Enrichment (Gemini)**: Use **Gemini 2.5 Flash** to analyze images and generate professional morphological descriptions (captions) and specific color labels. This data is saved back to PostgreSQL.
- **Phase 5: Vector Indexing (Qdrant)**: Fetch enriched records from PostgreSQL, generate embeddings (Fashion-SigLIP), and push them to Qdrant.

### 3. Volume Mapping
- `pgdata`: Persistent PostgreSQL storage.
- `qdrant_data`: Persistent Vector DB storage.
- `./images`: Host directory containing fashion product images, mounted as read-only.
- `./models`: Local cache for embedding models (~1GB).

## Hardware Considerations
- Since the user is on a Mac (likely M-series based on paths), we will utilize MPS (Metal Performance Shaders) or CPU for the BGE Reranker if Docker allows, though standard CPU execution is the default for compatibility.
- 16GB RAM recommended for smooth operation of all models simultaneously.
