# Proposal: Setup Self-Hosting for Fashion Agent

## Goal
Enable the user to self-host the Fashion Agent multimodal RAG system on their local Mac environment.

## Current Status
- Docker command is present but broken (symlink points to missing /Applications/Docker.app).
- `.env` file requires configuration for PostgreSQL and Gemini API.
- Data ingestion pipeline needs to be initialized.

## Proposed Changes
1. **Infrastructure**: Reinstall Docker Desktop and verify the `docker` command.
2. **Data Acquisition**: Download and extract the Kaggle dataset, targeting a subset of **5,000 items** for efficient processing.
3. **Resilient Pipeline**: Utilize the system's idempotent processing logic—if interrupted, scripts can be re-run to resume from the last processed item without duplication.
4. **Environment**: Configure the finalized `.env` file with required credentials.
5. **Deployment**: Orchestrate the 4-service stack via Docker Compose.
6. **Data Enrichment**: Enhance metadata using **Gemini 2.5 Flash** with built-in checkpointing via PostgreSQL.
7. **Vector Indexing**: Transform enriched data into vector embeddings and sync to **Qdrant**.

## Success Criteria
- User can access the Gradio UI at `localhost:8000`.
- System can retrieve fashion items based on text queries.
- Session memory persists in PostgreSQL.
