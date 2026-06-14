## ADDED Requirements

### Requirement: Canonical category resolution
The system SHALL resolve user-provided clothing category terms into one of the supported catalog category labels before category validation and retrieval.

#### Scenario: Exact supported category
- **WHEN** the user asks for a supported category using different casing such as "pants" or "PANTS"
- **THEN** the system resolves the category to the canonical label `Pants`

#### Scenario: Natural synonym category
- **WHEN** the user asks for a synonym of a supported category such as "trousers"
- **THEN** the system resolves the category to the canonical label `Pants`

#### Scenario: Common spelling mistake
- **WHEN** the user asks for a misspelled supported category such as "panst"
- **THEN** the system resolves the category to the canonical label `Pants` when the fuzzy match confidence meets the configured threshold

#### Scenario: Unsupported category remains unsupported
- **WHEN** the user asks for a category that cannot be confidently resolved to a supported catalog label
- **THEN** the system SHALL return the unsupported-category response without running hybrid search

### Requirement: Supported category validation remains authoritative
The system SHALL validate the resolved category against the supported catalog category set before executing BM25, vector retrieval, RRF fusion, or reranking.

#### Scenario: Resolved category passes validation
- **WHEN** a user category term resolves to a supported catalog category
- **THEN** the system SHALL continue to the normal search readiness checks and retrieval flow

#### Scenario: Unresolved category fails validation
- **WHEN** a user category term does not resolve to a supported catalog category
- **THEN** the system SHALL stop before retrieval and produce the unsupported-category response

### Requirement: Canonical filters for hybrid search
The system SHALL pass canonical category labels, not raw user category terms, into hybrid search filters.

#### Scenario: Synonym used in search filter
- **WHEN** the user asks for "black trousers"
- **THEN** the system SHALL search with a category filter of `Pants` and a color filter of `black`

#### Scenario: Typo used in search filter
- **WHEN** the user asks for "black panst"
- **THEN** the system SHALL search with a category filter of `Pants` if the typo resolves confidently

### Requirement: Retrieval query preserves useful natural terms
The system SHALL allow the retrieval query to include useful natural user terms alongside canonical labels when they improve keyword recall, while keeping filters canonical.

#### Scenario: Synonym retained for BM25 recall
- **WHEN** the user asks for "black trousers"
- **THEN** the system MAY search text containing both `black pants` and `trousers`, while the category filter remains `Pants`

### Requirement: Category-list questions bypass stale search slots
The system SHALL answer user questions about available catalog categories directly and SHALL NOT let stale accumulated category slots trigger unsupported-category refusals for those questions.

#### Scenario: User asks available categories after unsupported term
- **WHEN** the previous turn contained an unsupported or unresolved category and the user asks "what categories do you have?"
- **THEN** the system SHALL return the list of supported catalog categories instead of repeating the previous unsupported-category response

#### Scenario: User asks category list in a fresh session
- **WHEN** the user asks "give me your categories"
- **THEN** the system SHALL return the supported catalog categories without running product retrieval

### Requirement: Deterministic tests for category canonicalization
The system SHALL provide tests for exact category matching, synonym matching, typo correction, unsupported-category refusal, search filter canonicalization, and category-list behavior.

#### Scenario: Synonym tests cover common catalog terms
- **WHEN** the test suite runs category canonicalization tests
- **THEN** it SHALL verify mappings such as `trousers` to `Pants`, `tee` to `T-Shirt`, and `sneakers` to `Shoes`

#### Scenario: Unsupported tests prevent overmatching
- **WHEN** the test suite runs unsupported-category tests
- **THEN** it SHALL verify that unrelated categories such as `bag` are not silently mapped to a supported clothing category
