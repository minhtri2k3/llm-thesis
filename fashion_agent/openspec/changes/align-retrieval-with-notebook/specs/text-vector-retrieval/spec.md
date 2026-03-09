## ADDED Requirements

### Requirement: Text Embedding Encoding
The indexing pipeline SHALL encode text metadata (`label + ". " + color + ". " + caption`) into a 768-d vector using FashionSigLIP text encoder, for every item that has a caption.

#### Scenario: Item with full metadata
- **WHEN** an item has label="Shirt", color="Charcoal Grey", caption="Relaxed-fit woven cotton pullover with ribbed hem"
- **THEN** the system SHALL encode the string `"Shirt. Charcoal Grey. Relaxed-fit woven cotton pullover with ribbed hem"` via `FashionEmbedder.encode_text()` and store the resulting 768-d vector in Qdrant as a named vector `"text"`.

#### Scenario: Item without caption
- **WHEN** an item has label="Dress", color="Red", caption is NULL or empty
- **THEN** the system SHALL encode `"Dress. Red."` (same as BM25 content) as the text vector.

### Requirement: Qdrant Named Vectors
The Qdrant collection SHALL use named vectors with two vector spaces: `"image"` (768-d, image encoding) and `"text"` (768-d, text encoding). Both vectors SHALL share the same payload.

#### Scenario: Collection initialization
- **WHEN** `init_collection()` is called and collection does not exist
- **THEN** the system SHALL create a collection with named vectors config: `{"image": {size: 768, distance: Cosine}, "text": {size: 768, distance: Cosine}}`.

#### Scenario: Point upsert
- **WHEN** a new item is indexed
- **THEN** the system SHALL upsert a point with both `"image"` and `"text"` named vectors, plus the full payload (image_id, label, color, caption, image_path, bm25_content).

### Requirement: Text Vector Retrieval
The search engine SHALL provide a `text_vector_retrieve()` function that encodes the query text via SigLIP text encoder and performs ANN search against the `"text"` named vector in Qdrant.

#### Scenario: Text vector search
- **WHEN** `text_vector_retrieve("white cotton shirt", top_k=20)` is called
- **THEN** the system SHALL encode the query, search the `"text"` named vector space, and return up to 20 `NodeWithScore` results sorted by cosine similarity.

#### Scenario: Independence from image vector
- **WHEN** text_vector_retrieve and vector_retrieve (image) are called with the same query
- **THEN** the results MAY differ because they search different vector spaces (text semantics vs visual semantics).
