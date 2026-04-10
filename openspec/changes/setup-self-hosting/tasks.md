# Tasks: Self-Hosting Implementation

## Priority 1: Infrastructure
- [ ] Install/Reinstall Docker Desktop for Mac.
- [ ] Verify `docker --version` and `docker compose version`.
- [ ] Ensure Docker has at least 8GB RAM allocated in settings.

## Priority 2: Configuration & Data
- [ ] Create `fashion_agent/.env` file with proper credentials.
- [x] Prepare Directories: `mkdir -p fashion_agent/images fashion_agent/models`.
- [ ] Download [Kaggle Dataset](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset).
- [ ] Extract and place images in `fashion_agent/images/`.
- [ ] Place `styles.csv` in `fashion_agent/`. 

## Priority 3: Deployment
- [x] Run `docker compose up -d postgres qdrant`.
- [x] Wait for healthy status: `docker compose ps`.
- [ ] Run `docker compose up -d --build fashion-api`.

## Priority 4: Data Pipeline
> [!TIP]
> All scripts below are resumable. If a step fails or is stopped, simply run it again to continue from the last checkpoint.
- [ ] **Step 1: Raw Ingestion**: `docker exec -it fashion-api python -m pre_processing.processing_data ingest-kaggle --limit 5000`
- [ ] **Step 2: Gemini Enrichment**: `docker exec -it fashion-api python -m pre_processing.processing_data process --captions --colors --limit 5000`
- [ ] **Step 3: Qdrant Collection Init**: `docker exec -it fashion-api python -m indexing.build_index init`
- [ ] **Step 4: Vector Indexing**: `docker exec -it fashion-api python -m indexing.build_index build --limit 5000`
- [ ] **Final Check**: Verify via Health Check: `curl http://localhost:8000/health` or `docker exec -it fashion-api python -m indexing.build_index status`.
