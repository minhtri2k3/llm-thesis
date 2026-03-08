## ADDED Requirements

### Requirement: FashionSigLIP image encoding
The system SHALL encode fashion images using `Marqo/marqo-fashionSigLIP` model, producing 768-dimensional vectors (FP16).

#### Scenario: Single image encoding
- **WHEN** an image file path is provided to the encoder
- **THEN** the system returns a 768-dimensional float vector representing the image

#### Scenario: Batch image encoding
- **WHEN** a list of image file paths is provided
- **THEN** the system encodes all images in batches (batch_size configurable, default 32) and returns a list of 768d vectors

### Requirement: Query text encoding
The system SHALL encode user query text using the same FashionSigLIP model to produce a 768-dimensional vector for semantic search.

#### Scenario: Query encoding
- **WHEN** a text query "white formal shirt" is provided
- **THEN** the system returns a 768-dimensional float vector in the same embedding space as image vectors

### Requirement: Qdrant collection creation
The system SHALL create a Qdrant collection named `fashion_products` with vector size 768 and cosine distance metric.

#### Scenario: Collection initialization
- **WHEN** `build_index.py init` is executed
- **THEN** a Qdrant collection `fashion_products` is created with vector_size=768, distance=Cosine, and HNSW index

### Requirement: Vector upsert from PostgreSQL
The system SHALL read items from PostgreSQL (fashion_items + fashion_item_enrichment), encode images, compose payloads, and upsert into Qdrant.

#### Scenario: Full index build
- **WHEN** `build_index.py build` is executed
- **THEN** for each item in PostgreSQL with a valid image_path:
  1. Image is encoded to 768d vector via FashionSigLIP
  2. Payload is composed: {image_id, label, color, caption, image_path, bm25_content}
  3. bm25_content is composed as `"{label}. {color}."`
  4. Vector + payload are upserted into Qdrant collection

#### Scenario: Incremental indexing
- **WHEN** `build_index.py build` is executed and some items are already indexed
- **THEN** only items not yet in Qdrant are encoded and upserted (skip existing point_ids)

### Requirement: BM25 index construction
The system SHALL build a BM25 index over `bm25_content` fields for keyword-based retrieval.

#### Scenario: BM25 index build
- **WHEN** `build_index.py build` completes vector upsert
- **THEN** a BM25 index is constructed from all `bm25_content` values, mapping document IDs to their BM25 tokens

### Requirement: Model caching
Downloaded HuggingFace models SHALL be cached in a local `models/` directory to avoid re-downloading on container restart.

#### Scenario: Model persistence
- **WHEN** Docker container restarts
- **THEN** FashionSigLIP model files are loaded from the mounted `models/` volume without downloading again
