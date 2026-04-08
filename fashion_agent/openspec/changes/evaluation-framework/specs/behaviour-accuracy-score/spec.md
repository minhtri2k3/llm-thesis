## ADDED Requirements

### Requirement: Selection Rate computation
The system SHALL compute Selection Rate (SR) per orchestration mode as the fraction of sessions where `jsonb_array_length(liked_items) > 0`.

#### Scenario: Session with at least one selection counted
- **WHEN** a session has `liked_items = ["img_1", "img_2"]`
- **THEN** that session is counted in the SR numerator for its mode

#### Scenario: Session with no selections excluded from numerator
- **WHEN** a session has `liked_items = []` or is NULL
- **THEN** that session is NOT counted in the SR numerator, but IS counted in the denominator

### Requirement: Session Completion Rate computation
The system SHALL compute Session Completion Rate (SCR) per mode as the fraction of sessions where `ended_by IN ('order', 'rating')`.

#### Scenario: Order session counted as complete
- **WHEN** `ended_by = 'order'`
- **THEN** session is counted in SCR numerator

#### Scenario: Timeout session not counted as complete
- **WHEN** `ended_by = 'timeout'` or `ended_by IS NULL`
- **THEN** session is NOT counted in SCR numerator

### Requirement: Query Refinement Rate computation
The system SHALL compute Query Refinement Rate (QRR) per mode as the average number of entries in `query_history` per session.

#### Scenario: Single-turn sessions have QRR of 1
- **WHEN** a session has exactly one entry in `query_history`
- **THEN** that session contributes 1 to the QRR average

#### Scenario: Higher QRR indicates more follow-up queries
- **WHEN** a session has 4 entries in `query_history`
- **THEN** that session contributes 4 to the QRR average for its mode

### Requirement: Behaviour accuracy API endpoint
The system SHALL expose `GET /api/analytics/accuracy` returning SR, SCR, and QRR per `orchestration_mode`, `preferred_model`, and `n_sessions`.

#### Scenario: Response includes all four behaviour signals
- **WHEN** client calls `GET /api/analytics/accuracy`
- **THEN** response JSON contains `selection_rate_pct`, `completion_rate_pct`, `avg_queries_per_session` per mode row

#### Scenario: Modes with no sessions return empty array
- **WHEN** no sessions exist for a given orchestration mode
- **THEN** that mode does not appear in the response array
