## MODIFIED Requirements

### Requirement: Reranker Score Blending
The `BGEReranker.rerank()` method SHALL blend cross-encoder scores with original RRF scores using the formula: `final_score = 0.7 × reranker_score + 0.3 × original_rrf_score`.

#### Scenario: Normal reranking
- **WHEN** reranker scores a node with reranker_score=0.85 and original rrf_score=0.042
- **THEN** the final score SHALL be `0.7 × 0.85 + 0.3 × 0.042 = 0.6076`.

#### Scenario: Score normalization
- **WHEN** reranker scores are on a different scale than RRF scores
- **THEN** the system SHALL normalize reranker scores to [0, 1] range (min-max normalization within the batch) before blending, to ensure fair combination with RRF scores.

#### Scenario: Single candidate
- **WHEN** only 1 candidate node is provided
- **THEN** the system SHALL assign it the reranker score directly (normalization not applicable with single item).
