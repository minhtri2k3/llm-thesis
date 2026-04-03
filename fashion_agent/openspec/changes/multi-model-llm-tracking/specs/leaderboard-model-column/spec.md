## ADDED Requirements

### Requirement: Leaderboard returns model name and token count
The `GET /api/ratings` endpoint SHALL include `model_name` (string, from `session_token_summary.model_name`) and `total_tokens` (integer) for each leaderboard entry.

#### Scenario: Entry with token data
- **WHEN** a session has LLM token usage logged and the user submitted a rating
- **THEN** the leaderboard entry includes `"model_name": "gemini-2.5-flash"` and `"total_tokens": 1234`

#### Scenario: Entry with no token data
- **WHEN** a session has a rating but no token usage records
- **THEN** the entry includes `"model_name": null` (or empty string) and `"total_tokens": 0`

### Requirement: Leaderboard UI shows model badge
The `_LeaderboardDialog` Flutter widget SHALL display a visible model badge or chip for each entry showing the model name. Entries without model data SHALL show "—".

#### Scenario: Model badge rendered
- **WHEN** the leaderboard dialog is opened
- **THEN** each row shows the user name, rating stars, and a model badge (e.g., "Gemini", "GPT-4o", "Claude")

#### Scenario: No model shown as placeholder
- **WHEN** an entry has no model name
- **THEN** a "—" placeholder is shown in the model column
