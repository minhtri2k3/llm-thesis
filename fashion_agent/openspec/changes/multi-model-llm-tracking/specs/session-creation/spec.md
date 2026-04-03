## MODIFIED Requirements

### Requirement: Session creation accepts preferred model
`POST /api/sessions` SHALL accept an optional `preferred_model: str` field (default `"gemini-2.5-flash"`). The field SHALL be validated against the allowlist `["gemini-2.5-flash", "gpt-4o", "claude-3-5-sonnet-20241022"]`. Unknown values SHALL be silently replaced with the default. The `user_sessions` table SHALL have a `preferred_model TEXT DEFAULT 'gemini-2.5-flash'` column.

#### Scenario: Session created with Gemini (existing default behaviour)
- **WHEN** `POST /api/sessions` is called with `{"user_name": "Alice", "year_of_birth": 2000, "gender": "female"}`
- **THEN** session is created with `preferred_model = "gemini-2.5-flash"` (backward compatible)

#### Scenario: Session created with GPT-4o
- **WHEN** `POST /api/sessions` is called with `preferred_model: "gpt-4o"`
- **THEN** `user_sessions.preferred_model = "gpt-4o"` is stored

#### Scenario: Session created with invalid model
- **WHEN** `POST /api/sessions` is called with `preferred_model: "invalid-model"`
- **THEN** session is created with `preferred_model = "gemini-2.5-flash"` and HTTP 200 returned
