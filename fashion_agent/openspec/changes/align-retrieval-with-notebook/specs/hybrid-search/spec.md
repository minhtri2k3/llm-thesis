## MODIFIED Requirements

### Requirement: RRF Fusion Weights
The `reciprocal_rank_fusion()` function SHALL support 3-way fusion (BM25 + text vector + image vector) with default weights: `bm25_weight=2.5`, `text_vec_weight=1.5`, `img_vec_weight=1.0`.

#### Scenario: 3-way fusion
- **WHEN** BM25, text_vector, and image_vector results are provided
- **THEN** the system SHALL compute RRF score as: `bm25_weight × 1/(k+rank_bm25+1) + text_vec_weight × 1/(k+rank_text+1) + img_vec_weight × 1/(k+rank_img+1)` and return results sorted by fused score descending.

#### Scenario: Backward compatibility (2-way)
- **WHEN** text_vector results are empty (e.g., index not yet rebuilt)
- **THEN** the system SHALL fallback to 2-way fusion (BM25 + image vector) using `bm25_weight=2.5, img_vec_weight=1.0`.

### Requirement: Search Pipeline Integration
The `search()` function SHALL orchestrate: query expansion → 3-way retrieval (BM25 + text vector + image vector) → dedup → 3-way RRF fusion → soft filter → reranker.

#### Scenario: Full pipeline with text vectors
- **WHEN** `search("white cotton shirt")` is called and Qdrant has named vectors
- **THEN** the system SHALL call `bm25_retrieve()`, `text_vector_retrieve()`, and `vector_retrieve()` for each expanded query, then fuse all 3 result sets.

### Requirement: Filter-aware Soft Scoring
The `search()` function SHALL accept an optional `filters: dict` parameter. When provided, soft filter SHALL multiply each node's RRF score by a filter relevance factor based on category/color match.

#### Scenario: Filters provided
- **WHEN** `search("white shirt", filters={"category": "Shirt", "color": "white"})` is called
- **THEN** nodes whose label matches "Shirt" AND color matches "white" SHALL receive relevance=1.0. Partial matches SHALL receive proportional scores (0.0-1.0). The node's final score SHALL be `rrf_score × filter_relevance`.

#### Scenario: No filters
- **WHEN** `search("casual outfit")` is called without filters
- **THEN** the system SHALL use the existing RapidFuzz fuzzy match as fallback soft filter.
