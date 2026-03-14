## ADDED Requirements

### Requirement: Search Output Bounds Constrainment
The search pipeline limits must be strictly updated to enforce narrower constraint values for initial retrieval and final candidate selection phases.

#### Scenario: Sub-retrieval and Semantic Reranker execution limits
- **WHEN** the search engine invokes retrieval across BM25, Text Vector, Image Vector 
- **THEN** each channel generates top 5 results maximum, and the post-fusion Reranker limits the final subset sequence block exclusively to 3 results.
