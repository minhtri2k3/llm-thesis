## ADDED Requirements

### Requirement: PATH 2 MUST support direct cart insertion
The system SHALL provide a dedicated API contract that inserts PATH 2 products into the session cart without conversational product-selection parsing.

#### Scenario: Direct PATH 2 add-to-cart succeeds
- **WHEN** the client sends a valid direct selection request containing session, product payload, and `path_mode=path2`
- **THEN** the system SHALL persist the selected item and return a successful insertion response

#### Scenario: Invalid direct selection request is rejected
- **WHEN** the client sends a direct selection request with missing or invalid required fields
- **THEN** the system SHALL return a validation error and SHALL NOT persist a cart selection

### Requirement: Direct PATH 2 cart adds MUST be visible in cart retrieval
Selections inserted through the direct PATH 2 contract SHALL be returned by the session selections API.

#### Scenario: Cart list includes direct PATH 2 selection
- **WHEN** a direct PATH 2 add-to-cart request succeeds
- **THEN** subsequent cart retrieval for that session SHALL include the inserted item with `path_mode=path2`

### Requirement: PATH attribution MUST remain consistent for direct PATH 2 adds
Direct PATH 2 cart insertions SHALL preserve path attribution used by analytics and downstream funnel metrics.

#### Scenario: Direct selection preserves path mode
- **WHEN** analytics or session funnel aggregation reads selections created by the direct PATH 2 contract
- **THEN** the selected records SHALL be attributed to `path_mode=path2`

