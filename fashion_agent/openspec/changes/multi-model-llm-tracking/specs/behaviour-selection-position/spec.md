## ADDED Requirements

### Requirement: Selected item records reranker position
The `selected_items` table SHALL include a `position INT NOT NULL DEFAULT 0` column. When `_handle_confirm()` saves an item, the system SHALL look up the most recent `product_clicks.position` for `(session_id, image_id)` and store it in `selected_items.position`.

#### Scenario: Position captured from click log
- **WHEN** user taps image at position 2, then confirms the selection
- **THEN** `selected_items.position = 2` for that `(session_id, image_id)` row

#### Scenario: No prior click defaults to 0
- **WHEN** an item is confirmed but no click event exists for it
- **THEN** `selected_items.position = 0`

### Requirement: Behaviour funnel exposes position data
The `/api/analytics/behaviour-funnel` endpoint SHALL include `avg_position_selected` (mean `selected_items.position` for the session, excluding 0s) per session row to enable reranker precision analysis.

#### Scenario: Precision metric computed
- **WHEN** a session has two saved items at positions 1 and 3
- **THEN** `avg_position_selected = 2.0` in the funnel analytics for that session
