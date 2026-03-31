## ADDED Requirements

### Requirement: Capture year of birth at session creation
The system SHALL accept a `year_of_birth` integer from the client at session-creation time and persist it to `user_sessions.year_of_birth`. The value SHALL be validated: `1900 ≤ year_of_birth ≤ current_year`.

#### Scenario: Valid year of birth submitted
- **WHEN** a client sends `POST /api/sessions` with `year_of_birth: 1998`
- **THEN** the session is created and `user_sessions.year_of_birth` is set to `1998`

#### Scenario: Missing year of birth
- **WHEN** a client sends `POST /api/sessions` without `year_of_birth`
- **THEN** the session is created with `user_sessions.year_of_birth = NULL`

#### Scenario: Invalid year of birth (too early)
- **WHEN** a client sends `POST /api/sessions` with `year_of_birth: 1800`
- **THEN** the API returns HTTP `422 Unprocessable Entity`

#### Scenario: Invalid year of birth (future)
- **WHEN** a client sends `POST /api/sessions` with `year_of_birth` greater than the current year
- **THEN** the API returns HTTP `422 Unprocessable Entity`

---

### Requirement: Capture gender at session creation
The system SHALL accept a `gender` string (`"male"` or `"female"`) from the client at session-creation time and persist it to `user_sessions.gender`. Any other value SHALL be rejected.

#### Scenario: Valid gender submitted
- **WHEN** a client sends `POST /api/sessions` with `gender: "female"`
- **THEN** the session is created and `user_sessions.gender` is set to `"female"`

#### Scenario: Missing gender
- **WHEN** a client sends `POST /api/sessions` without `gender`
- **THEN** the session is created with `user_sessions.gender = NULL`

#### Scenario: Invalid gender value
- **WHEN** a client sends `POST /api/sessions` with `gender: "nonbinary"`
- **THEN** the API returns HTTP `422 Unprocessable Entity`

---

### Requirement: Flutter registration form collects demographics
The Flutter `RegisterScreen` SHALL present a birth year input field and a binary gender selector (labelled "Boy" and "Girl") before the user can start chatting.

#### Scenario: User fills all fields and starts chat
- **WHEN** a user enters a name, a valid birth year, selects a gender, and taps "Start Chatting"
- **THEN** the app calls `createSession` with all three values and navigates to `ChatScreen`

#### Scenario: User submits without birth year
- **WHEN** a user leaves the birth year field empty and taps "Start Chatting"
- **THEN** the app shows an inline validation error and does not call the API

#### Scenario: User submits without gender selection
- **WHEN** a user has not selected a gender and taps "Start Chatting"
- **THEN** the app shows an inline validation error and does not call the API

#### Scenario: Invalid birth year entered
- **WHEN** a user enters a birth year outside the range 1900–current year
- **THEN** the app shows an inline validation error and does not call the API

---

### Requirement: DB schema stores demographics
The `user_sessions` table SHALL have two nullable columns: `year_of_birth INT` and `gender TEXT CHECK (gender IN ('male', 'female'))`, added via idempotent `ALTER TABLE … ADD COLUMN IF NOT EXISTS` at application startup.

#### Scenario: First startup adds columns
- **WHEN** the backend starts for the first time after deployment
- **THEN** `user_sessions` gains `year_of_birth` and `gender` columns without error

#### Scenario: Subsequent startups are no-ops
- **WHEN** the backend restarts with columns already present
- **THEN** `init_memory_tables()` completes without error or data loss
