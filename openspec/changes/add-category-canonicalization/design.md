## Context

The deployed agent uses direct routing: Gemini classifies intent and extracts slots, `_resolve_search_query()` merges slots and validates category, then `hybrid_search()` runs BM25, image-vector ANN, text-vector ANN, RRF fusion, and BGE reranking. Category validation currently checks the extracted category against `SUPPORTED_CATEGORIES` by exact string match before retrieval. This protects the index from unsupported labels, but it also blocks valid user language that does not exactly match the database label set.

The catalog ontology contains 17 canonical labels. The database and Qdrant payloads use those labels, so the retrieval layer needs canonical category values such as `Pants`, not natural variants such as `trousers` or misspellings such as `panst`.

## Goals / Non-Goals

**Goals:**
- Normalize natural category terms and spelling variants into canonical catalog labels before validation.
- Keep the 17 supported category labels as the final retrieval ontology.
- Improve BM25 and hybrid RAG recall for synonym-heavy user queries.
- Prevent stale invalid category slots from repeatedly blocking category-list questions.
- Provide deterministic, testable behavior for common synonyms and typos.
- Use Gemini for semantic extraction, but not as the only authority for final database labels.

**Non-Goals:**
- Do not add new catalog categories or re-index the dataset.
- Do not change Qdrant vector schema or Postgres product schema.
- Do not remove unsupported-category protection.
- Do not rely on an additional Gemini call for every category normalization.
- Do not redesign the full intent classification pipeline.

## Decisions

### Decision 1: Add deterministic canonicalization after Gemini extraction

Gemini should continue extracting a raw category phrase from the user message. A deterministic canonicalization helper should then convert that raw phrase to a canonical catalog label before `_resolve_search_query()` validates it.

Rationale: Gemini is good at semantic extraction, but the index uses a closed ontology. A deterministic layer keeps retrieval stable, avoids extra latency, and makes tests reproducible.

Alternative considered: ask Gemini to map every category directly to one of the 17 labels. This can work, but it adds latency and still requires validation because Gemini can output unsupported labels or ambiguous mappings.

### Decision 2: Use a three-stage category resolver

The resolver should attempt category resolution in this order:

1. Exact canonical label match, case-insensitive.
2. Exact synonym map match for known user vocabulary.
3. RapidFuzz typo match against canonical labels and synonym keys with a conservative threshold.

If no confident match exists, the existing unsupported-category response path should run.

Rationale: exact and synonym matches handle predictable cases safely. Fuzzy matching handles misspellings such as `panst` without making the LLM responsible for spelling correction. A conservative threshold reduces false positives.

Alternative considered: only use fuzzy matching. This is risky for short or ambiguous terms because unrelated words can match a category by accident.

### Decision 3: Keep synonym mapping close to the category ontology

The synonym map should live near `SUPPORTED_CATEGORIES` in `agent/utils.py`, not inside prompts or search code.

Rationale: this makes the catalog vocabulary explicit and keeps all category-related logic in one place. It also matches the existing unsupported-category helper location.

Alternative considered: place synonyms in the intent prompt. That increases prompt length, is harder to test, and still cannot guarantee canonical output.

### Decision 4: Canonicalize both slots and filters

The same canonical category should be applied to:
- accumulated slot state
- ranked slots
- `intent_result.filters["category"]`
- final search query construction where category appears

Rationale: retrieval has two category paths: the query text and the filter-aware scoring in `search_engine.py`. If only one path is canonicalized, BM25 or filter scoring can still behave inconsistently.

### Decision 5: Add category-list behavior before search gating

Queries asking what categories are available should return the supported category list directly. This behavior should bypass stale accumulated category slots so a previous invalid category like `Trousers` cannot cause repeated refusals.

Rationale: a catalog metadata question is not a product search. Treating it as `follow_up` or `text_search` causes the current stale-slot failure.

Alternative considered: handle category-list questions only in the synthesis prompt after search. That is too late because the current failure happens before search and synthesis.

### Decision 6: Query expansion should include canonical and natural terms

When a synonym is canonicalized, the search query may include both the canonical label and the user synonym where useful, such as `black pants trousers`. The filter should use only the canonical label.

Rationale: the filter needs schema correctness, while BM25 benefits from natural vocabulary that may appear in captions or BM25 content.

## Risks / Trade-offs

- False-positive fuzzy corrections → Use a conservative threshold and prefer exact synonym entries for common terms.
- Ambiguous terms like `jacket` → Map only when the product ontology has a clear intended category, or return suggestions / clarification for multi-category terms.
- Synonym map maintenance → Keep it small, focused on catalog vocabulary, and covered by tests.
- Multilingual category terms → Start with English terms already seen in the app; future work can add Vietnamese and Spanish synonyms without changing the design.
- Stale slots still affecting other non-search questions → Category-list handling should explicitly bypass accumulated search slots; broader metadata intent handling can be added later.

## Migration Plan

1. Add canonicalization helpers and synonym data in `agent/utils.py`.
2. Apply canonicalization in `_resolve_search_query()` before unsupported-category validation.
3. Apply the canonical category to filters before `_route_and_execute()` calls `hybrid_search()`.
4. Add category-list detection and response before search readiness gating.
5. Add tests for supported labels, synonyms, typos, unsupported terms, category-list questions, and stale-slot recovery.
6. Deploy with no database migration and no re-indexing.

Rollback is local: remove the canonicalization calls and helper additions. Existing exact-match validation remains the fallback behavior.

## Open Questions

- Should ambiguous terms such as `jacket` map directly to `Outwear`, or should the agent ask whether the user means `Outwear`, `Blazer`, or `Hoodie`?
- Should Vietnamese and Spanish clothing synonyms be included in the first implementation or added after English validation passes?
- Should category-list responses include only category names, or short user-friendly descriptions for each category?
