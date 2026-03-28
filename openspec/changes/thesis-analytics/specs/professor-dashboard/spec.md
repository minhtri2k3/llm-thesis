## ADDED Requirements

### Requirement: Professor View button on Register screen
The Flutter Register screen SHALL display a "🔬 Professor View" button below the existing "🏆 Leaderboard" button. Tapping it SHALL open an 8-digit PIN dialog before loading any analytics data.

#### Scenario: Button is visible on Register screen
- **WHEN** the user views the Register screen
- **THEN** a "🔬 Professor View" button is visible below the Leaderboard button

#### Scenario: Tapping the button opens PIN dialog
- **WHEN** the user taps "🔬 Professor View"
- **THEN** a modal dialog appears with an obscured text field labeled "Enter access code"

### Requirement: PIN dialog validates the ADMIN_SECRET_KEY
The PIN dialog SHALL send the entered code to the backend analytics endpoint. If the backend returns 200, the dialog SHALL close and the analytics dashboard SHALL open. If the backend returns 403, the dialog SHALL display an "Incorrect code" error in-place.

#### Scenario: Correct PIN entered
- **WHEN** the user enters "21042024" and taps "Unlock"
- **THEN** the PIN dialog closes and the Professor Dashboard opens

#### Scenario: Incorrect PIN entered
- **WHEN** the user enters any value other than "21042024" and taps "Unlock"
- **THEN** the dialog remains open and displays "Incorrect access code" error text

#### Scenario: Empty PIN submitted
- **WHEN** the user taps "Unlock" without entering any text
- **THEN** the dialog shows a validation error "Enter the access code" without making a network call

### Requirement: Professor Dashboard displays per-session token analytics
The Professor Dashboard dialog SHALL render a scrollable list of sessions. Each row SHALL display: Session ID (truncated to 12 characters), User Name, Model Name, and Total Tokens spent.

#### Scenario: Dashboard loads with data
- **WHEN** the backend returns a non-empty list of session analytics
- **THEN** each session is rendered as a row with Session ID, User Name, Model Name, and Total Tokens

#### Scenario: Dashboard shows empty state
- **WHEN** the backend returns an empty sessions list
- **THEN** the dashboard displays a "No sessions recorded yet." message

#### Scenario: Dashboard shows loading state
- **WHEN** the analytics data is being fetched
- **THEN** a `CircularProgressIndicator` is shown in place of the list

### Requirement: Backend analytics endpoint is protected by ADMIN_SECRET_KEY
The `GET /api/analytics/token-usage` endpoint SHALL require an `X-Admin-Key` HTTP header. If the header is absent or does not match `ADMIN_SECRET_KEY` from the environment, the endpoint SHALL return HTTP 403. If the `ADMIN_SECRET_KEY` environment variable is not set, the endpoint SHALL return HTTP 503.

#### Scenario: Valid admin key accepted
- **WHEN** a request arrives with `X-Admin-Key: 21042024` and the server has `ADMIN_SECRET_KEY=21042024`
- **THEN** the endpoint returns HTTP 200 with the session analytics payload

#### Scenario: Missing or wrong key rejected
- **WHEN** a request arrives with a missing or incorrect `X-Admin-Key`
- **THEN** the endpoint returns HTTP 403 with `{"detail": "Forbidden"}`

#### Scenario: Server-side key not configured
- **WHEN** `ADMIN_SECRET_KEY` is not set in the environment
- **THEN** the endpoint returns HTTP 503 with `{"detail": "Analytics not configured"}`
