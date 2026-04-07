## ADDED Requirements

### Requirement: Gender hint injection
The system SHALL fetch the user's declared gender from `user_sessions.gender` and, when `gender_hint_enabled = TRUE` for the session, include it as a dedicated context block in the synthesis prompt. The context block SHALL follow the format: `User profile: gender = {male|female}. Prioritize {menswear|womenswear} appropriate items.`

#### Scenario: Gender hint enabled for male user
- **WHEN** the session has `gender_hint_enabled = TRUE` and `gender = 'male'`
- **THEN** the synthesis prompt SHALL include `User profile: gender = male. Prioritize menswear appropriate items.`

#### Scenario: Gender hint enabled for female user
- **WHEN** the session has `gender_hint_enabled = TRUE` and `gender = 'female'`
- **THEN** the synthesis prompt SHALL include `User profile: gender = female. Prioritize womenswear appropriate items.`

#### Scenario: Gender hint disabled
- **WHEN** the session has `gender_hint_enabled = FALSE`
- **THEN** the gender field SHALL NOT appear in the synthesis prompt in any form

#### Scenario: Gender not provided
- **WHEN** the user did not declare gender during session creation (`gender = NULL`)
- **THEN** the gender block SHALL be omitted from the prompt regardless of `gender_hint_enabled`

---

### Requirement: A/B control group assignment
The system SHALL randomly assign `gender_hint_enabled` (TRUE/FALSE, 50/50 probability) to each new session at creation time and persist this value for the lifetime of the session.

#### Scenario: New session created
- **WHEN** a new session is created via `POST /api/sessions`
- **THEN** `gender_hint_enabled` SHALL be set to TRUE or FALSE with equal probability (~50/50) and stored in `user_sessions`

#### Scenario: Assignment is immutable
- **WHEN** a session already has `gender_hint_enabled` set
- **THEN** the value SHALL NOT change for any subsequent turn in that session

---

### Requirement: Post-hoc gender alignment measurement
The system SHALL store sufficient data to compute gender alignment rate post-hoc: the percentage of selected items that can be inferred as gender-appropriate based on item label.

#### Scenario: Selection recorded with session gender metadata
- **WHEN** a user selects one or more items in a session
- **THEN** `selected_items.session_id` SHALL link to `user_sessions.gender` and `user_sessions.gender_hint_enabled`, enabling cross-analysis via SQL JOIN
