## ADDED Requirements

### Requirement: BM25 keyword retrieval
The system SHALL perform BM25 keyword search over `bm25_content` fields, returning top-20 results ranked by term frequency score.

#### Scenario: BM25 search
- **WHEN** user query "white shirt" is tokenized and searched via BM25
- **THEN** system returns up to 20 NodeWithScore objects, each containing text, metadata (image_id, label, color, caption, image_path), and BM25 score

### Requirement: Vector ANN retrieval
The system SHALL perform approximate nearest neighbor search in Qdrant using the query vector (768d), returning top-20 results ranked by cosine similarity.

#### Scenario: Vector search
- **WHEN** user query is encoded to 768d vector and searched in Qdrant
- **THEN** system returns up to 20 NodeWithScore objects with cosine similarity scores (0.0 - 1.0)

### Requirement: RRF Fusion
The system SHALL merge BM25 and Vector results using Reciprocal Rank Fusion with k=60 and configurable weights (default: bm25_weight=1.0, vec_weight=2.5).

#### Scenario: Dual result merging
- **WHEN** BM25 returns 20 results and Vector returns 20 results
- **THEN** system produces a merged list of unique nodes with RRF scores: `score = bm25_weight * 1/(k + rank_bm25 + 1) + vec_weight * 1/(k + rank_vec + 1)`

#### Scenario: Single-source result
- **WHEN** a node appears only in BM25 results (not in Vector)
- **THEN** node receives RRF score using only its BM25 rank (vector rank term = 0)

### Requirement: Soft Relevance Filter
The system SHALL apply a soft relevance filter using RapidFuzz fuzzy string matching on color and category fields, removing nodes below a configurable threshold (default: 60).

#### Scenario: Color match filtering
- **WHEN** user query contains "white" and a node has color "Off-White"
- **THEN** fuzzy match score is computed (e.g., 85) and node is KEPT (above threshold 60)

#### Scenario: Irrelevant removal
- **WHEN** user query contains "red dress" and a node has label "Shoes" and color "Black"
- **THEN** fuzzy match score is low (e.g., 20) and node is REMOVED (below threshold 60)

### Requirement: BGE Reranker
The system SHALL apply `BAAI/bge-reranker-v2-m3` cross-encoder to rerank filtered nodes, returning the top-K results (default K=6).

#### Scenario: Rerank top results
- **WHEN** 15 nodes pass the soft filter
- **THEN** BGE reranker scores all 15 nodes using cross-encoder (query, document_text) pairs and returns the top-6 by relevance score

#### Scenario: Reranker input limit
- **WHEN** more than 20 nodes pass the soft filter
- **THEN** only the top-20 (by RRF score) are sent to the reranker to limit latency

### Requirement: Search pipeline orchestration
The system SHALL provide a single `search(query: str) -> List[NodeWithScore]` function that orchestrates the full pipeline: encode → dual retrieve → fuse → filter → rerank.

#### Scenario: End-to-end search
- **WHEN** `search("white formal shirt")` is called
- **THEN** system returns a list of up to 6 NodeWithScore objects, ordered by reranker score descending, each containing full product metadata
