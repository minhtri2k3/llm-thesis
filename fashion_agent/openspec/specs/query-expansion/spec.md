## ADDED Requirements

### Requirement: Gemini-powered query expansion
The system SHALL expand user search queries into multiple synonym/variation queries using Gemini 2.5 Flash before executing the hybrid search pipeline.

#### Scenario: Basic query expansion
- **WHEN** user searches "navy shirt"
- **THEN** system MUST generate up to 3 query variations (e.g., ["navy shirt", "dark blue shirt", "blue formal shirt"])
- **AND** original query MUST always be included in the expanded list

#### Scenario: Short query triggers expansion
- **WHEN** query contains fewer than 6 words
- **THEN** system MUST expand the query before searching

#### Scenario: Long query skips expansion
- **WHEN** query contains 6 or more words
- **THEN** system MUST skip expansion and use the original query directly to avoid latency

#### Scenario: Gemini API failure fallback
- **WHEN** Gemini API call fails (timeout, quota, network error)
- **THEN** system MUST fallback to using only the original query `[original_query]`
- **AND** system MUST NOT raise an exception or block the search pipeline

### Requirement: Multi-query search merge
The system SHALL execute BM25 + Vector retrieval for each expanded query and merge results before RRF fusion.

#### Scenario: Multi-query retrieval and dedup
- **WHEN** 3 expanded queries are generated
- **THEN** system MUST run BM25 retrieve for each query (3 calls)
- **AND** system MUST run Vector retrieve for each query (3 calls)
- **AND** results MUST be deduplicated by `image_id` before RRF fusion
- **AND** for duplicate `image_id`, the highest score MUST be kept

### Requirement: Query expansion module isolation
The `expand_query()` function SHALL live in a separate module `search/query_expansion.py` and have no dependencies on the agent layer.

#### Scenario: Module independence
- **WHEN** `search/query_expansion.py` is imported
- **THEN** it MUST NOT import from `agent/` package
- **AND** it MUST only depend on `google.generativeai` for LLM calls
