## ADDED Requirements

### Requirement: Path-attributed behavioral events
The system SHALL record behavioral events with explicit path attribution so analytics can distinguish PATH 1 and PATH 2 outcomes.

#### Scenario: PATH 1 event attribution
- **WHEN** a PATH 1 search result is shown and subsequent user interactions are logged
- **THEN** each recorded event SHALL include `path_mode=path1` and the session identifier

#### Scenario: PATH 2 event attribution
- **WHEN** a PATH 2 image-search result is returned and subsequent user interactions are logged
- **THEN** each recorded event SHALL include `path_mode=path2` and the session identifier

### Requirement: Full funnel coverage per path
The system SHALL capture impression, click, selection/cart, intent, and order signals for both PATH 1 and PATH 2 under a common telemetry contract.

#### Scenario: PATH 1 funnel capture
- **WHEN** a user completes a PATH 1 flow from search results to intent or order
- **THEN** funnel events SHALL be persisted in order with consistent session and path attribution

#### Scenario: PATH 2 funnel capture
- **WHEN** a user completes a PATH 2 flow from image-search results to intent or order
- **THEN** funnel events SHALL be persisted with the same event semantics as PATH 1 and with `path_mode=path2`

### Requirement: Path-scoped selection consistency
The system SHALL ensure selection confirmation is resolved against the result context of the same path where the product was presented.

#### Scenario: PATH 2 selection uses PATH 2 context
- **WHEN** a user selects an item originating from PATH 2 results
- **THEN** the confirmation/save flow SHALL resolve the selected item from PATH 2 result context, not PATH 1 cached context

#### Scenario: No cross-path selection leakage
- **WHEN** a session contains both PATH 1 and PATH 2 searches
- **THEN** selection resolution SHALL not map product indices across different path result sets
