## Why

The current agent validates extracted categories by exact string match against the catalog labels, so natural user terms and spelling mistakes such as "trousers", "trouser", "panst", "tshirt", or "sneakers" can be rejected before BM25 and hybrid RAG search runs. This creates a poor agent experience because the LLM understands the request semantically, but the retrieval layer only accepts the fixed database ontology.

## What Changes

- Add category canonicalization between intent extraction and category validation.
- Map common natural-language synonyms to the catalog's canonical category labels, such as trousers to Pants and tee to T-Shirt.
- Add deterministic fuzzy matching for minor spelling errors with a conservative confidence threshold.
- Keep SUPPORTED_CATEGORIES as the final source of truth for allowed database labels.
- Preserve unsupported-category handling for genuinely unavailable products, but improve suggestions when a close supported category exists.
- Add a category-list behavior so users asking what categories are available receive the supported catalog categories instead of stale search-slot refusals.
- Ensure canonical categories are applied consistently to search filters and query construction before BM25, vector retrieval, RRF fusion, and reranking.

## Capabilities

### New Capabilities
- `category-canonicalization`: Normalizes user category words, synonyms, and spelling variants into supported catalog category labels before validation and retrieval.

### Modified Capabilities

## Impact

- `fashion_agent/agent/utils.py`: category ontology helpers, synonym map, fuzzy canonicalization, and suggestion logic.
- `fashion_agent/agent/fashion_agent.py`: pre-search slot handling, category validation, stale invalid slot behavior, and category-list responses.
- `fashion_agent/agent/prompts.py`: intent guidance for category-list questions if needed.
- `fashion_agent/search/search_engine.py`: receives canonical category filters instead of raw user terms.
- Tests should cover synonym mapping, typo correction, unsupported categories, ambiguous category terms, stale slot recovery, and category-list questions.
