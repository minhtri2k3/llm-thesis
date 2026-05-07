## ADDED Requirements

### Requirement: Search readiness gate MUST run before query execution
For `text_search` and `follow_up` intents, the system SHALL evaluate readiness before running product retrieval.

#### Scenario: Low-confidence search request is clarified before search
- **WHEN** the classified intent is `text_search` or `follow_up` and confidence is below the configured threshold
- **THEN** the system SHALL return a clarification question and SHALL NOT execute a search query

#### Scenario: Sufficient-confidence search request proceeds
- **WHEN** the classified intent is `text_search` or `follow_up` and confidence meets or exceeds the configured threshold
- **THEN** the system SHALL continue to slot-readiness checks before deciding whether to execute search

### Requirement: Slot completeness MUST gate search execution
The system SHALL require minimum slot completeness before executing search for search-like intents.

#### Scenario: Missing required slots blocks query execution
- **WHEN** required slot criteria are not satisfied for a `text_search` or `follow_up` request
- **THEN** the system SHALL generate a targeted clarification question and SHALL NOT execute a search query

#### Scenario: Required slots allow query execution
- **WHEN** required slot criteria are satisfied for a `text_search` or `follow_up` request
- **THEN** the system SHALL execute search using the resolved query

### Requirement: Clarification responses MUST preserve conversational context
When readiness gating blocks execution, the system SHALL preserve accumulated slot context for the session.

#### Scenario: User provides missing details after clarification
- **WHEN** a follow-up user message provides missing slot details after a readiness clarification
- **THEN** the system SHALL merge new slot values with existing session slot context and re-evaluate readiness

