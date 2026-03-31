## ADDED Requirements

### Requirement: Ratings API includes demographic fields
`GET /api/ratings` SHALL include `year_of_birth` (INT or null) and `gender` (string or null) in each rating entry, sourced from the session's `user_sessions` row.

#### Scenario: Ratings entry has demographics
- **WHEN** a rating was submitted for a session that has `year_of_birth` and `gender`
- **THEN** `GET /api/ratings` returns those values in the entry's `year_of_birth` and `gender` fields

#### Scenario: Ratings entry lacks demographics
- **WHEN** a rating was submitted for a session without demographics (legacy or incomplete)
- **THEN** `GET /api/ratings` returns `year_of_birth: null` and `gender: null` for that entry

---

### Requirement: Demographics aggregate endpoint
The system SHALL provide `GET /api/demographics` (protected by `X-Admin-Key`) returning:
- Average rating and count grouped by gender (`"male"` | `"female"`)
- Average rating and count grouped by age group (`"Under 20"`, `"20-29"`, `"30-39"`, `"40+"`)

Only sessions where both `year_of_birth` and `gender` are non-null SHALL be included.

#### Scenario: Successful demographics fetch
- **WHEN** an admin calls `GET /api/demographics` with a valid `X-Admin-Key` header
- **THEN** the response contains `by_gender` and `by_age_group` arrays with avg. rating and count

#### Scenario: Unauthorized demographics fetch
- **WHEN** `GET /api/demographics` is called with an invalid or missing `X-Admin-Key`
- **THEN** the API returns HTTP `403 Forbidden`

#### Scenario: No demographic data available
- **WHEN** no sessions have demographics yet
- **THEN** `GET /api/demographics` returns empty `by_gender` and `by_age_group` arrays

---

### Requirement: Professor View shows demographics panel
The Flutter `_ProfessorDashboardDialog` SHALL display a demographics summary section showing avg. rating by gender and avg. rating by age group, loaded from `GET /api/demographics`.

#### Scenario: Demographics panel renders
- **WHEN** the professor dashboard loads successfully
- **THEN** a "Demographics" section is shown below the token analytics, displaying gender and age group breakdowns

#### Scenario: No demographics data
- **WHEN** `GET /api/demographics` returns empty arrays
- **THEN** the panel shows a "No demographic data yet" message
