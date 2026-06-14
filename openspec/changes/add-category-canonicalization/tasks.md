## 1. Category Ontology Helpers

- [x] 1.1 Add a canonical category lookup helper near `SUPPORTED_CATEGORIES` in `fashion_agent/agent/utils.py`.
- [x] 1.2 Add a focused synonym map for common user terms such as trousers, trouser, jeans, tee, tshirt, jacket, sneakers, and related catalog terms.
- [x] 1.3 Add conservative RapidFuzz typo matching against canonical labels and synonym keys.
- [x] 1.4 Return structured normalization metadata so callers can distinguish exact, synonym, fuzzy, and unresolved results.
- [x] 1.5 Update unsupported-category suggestions to reuse canonicalization where appropriate.

## 2. Agent Flow Integration

- [x] 2.1 Canonicalize extracted slot category values in `_resolve_search_query()` before unsupported-category validation.
- [x] 2.2 Canonicalize `intent_result.filters["category"]` before passing filters to hybrid search.
- [x] 2.3 Ensure accumulated slots and ranked slots store the canonical category label after successful normalization.
- [x] 2.4 Preserve unsupported-category early return for unresolved category terms.
- [x] 2.5 Prevent stale unresolved category slots from blocking non-search category-list questions.

## 3. Category List Behavior

- [x] 3.1 Add detection for category-list questions such as "what categories do you have?" and "give me your categories".
- [x] 3.2 Return the supported category list directly without running BM25, vector retrieval, RRF fusion, or reranking.
- [x] 3.3 Ensure category-list responses work after a previous unsupported category refusal in the same session.
- [x] 3.4 Keep the response language consistent with existing English, Vietnamese, and Spanish language handling where practical.

## 4. Retrieval Query and Filter Consistency

- [x] 4.1 Ensure search filters use only canonical category labels.
- [x] 4.2 Include useful natural terms in the search query when a synonym was normalized and it helps BM25 recall.
- [x] 4.3 Verify filter-aware scoring in `fashion_agent/search/search_engine.py` receives canonical category values.
- [x] 4.4 Keep existing query expansion behavior compatible with the new normalized query text.

## 5. Tests and Verification

- [x] 5.1 Add unit tests for exact category canonicalization.
- [x] 5.2 Add unit tests for synonym mappings including trousers to Pants, tee to T-Shirt, and sneakers to Shoes.
- [x] 5.3 Add unit tests for typo correction including panst to Pants.
- [x] 5.4 Add tests that unsupported terms such as bag are not silently mapped to supported clothing categories.
- [x] 5.5 Add agent-flow tests for black trousers producing a Pants category filter.
- [x] 5.6 Add agent-flow tests for category-list questions bypassing stale invalid slots.
- [x] 5.7 Run the relevant pytest files under `fashion_agent/tests/`.

## 6. Docker Refresh and Manual Runtime Verification

- [x] 6.1 Ask the user to rebuild or restart the `fashion-api` container after code changes so the running API loads the updated Python modules.
- [ ] 6.2 Verify the refreshed Docker runtime with `I need to find trousers` and confirm it searches `Pants` instead of returning the unsupported-category message.
- [ ] 6.3 Verify the refreshed Docker runtime with `what categories do you have?` after a previous trousers query and confirm it returns the category list instead of repeating stale refusal text.
- [x] 6.4 Do not run destructive Docker volume commands; use a refresh path that preserves Postgres and Qdrant data.

## 7. Documentation and Thesis Alignment

- [x] 7.1 Update any relevant thesis prose or methodology notes only if they currently describe exact category validation without canonicalization.
- [x] 7.2 Document the architecture as LLM semantic extraction plus deterministic ontology canonicalization, not Gemini-only category mapping.
