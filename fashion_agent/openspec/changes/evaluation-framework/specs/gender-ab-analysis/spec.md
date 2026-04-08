## ADDED Requirements

### Requirement: Gender Alignment Score endpoint
The system SHALL expose `GET /api/analytics/gender-ab` returning Gender Alignment Score (GAS) grouped by `gender_hint_enabled` (TRUE/FALSE) and `orchestration_mode`.

#### Scenario: Endpoint returns both A/B groups
- **WHEN** client calls `GET /api/analytics/gender-ab`
- **THEN** response includes rows for `gender_hint_enabled = true` and `gender_hint_enabled = false` with GAS and session counts

#### Scenario: GAS is null when no selections exist
- **WHEN** a group has sessions but no items in `liked_items`
- **THEN** GAS is returned as NULL or 0 for that group

### Requirement: Gender alignment calculation
GAS SHALL be computed as the fraction of selected items (entries in `liked_items`) whose gender category matches the session's `user_sessions.gender`, where gender is inferred from `fashion_items.gender` column if it exists, or from category name otherwise.

#### Scenario: Selected item matches gender — counted in numerator
- **WHEN** user.gender = 'female' and selected item has gender = 'female'
- **THEN** that selection is counted in GAS numerator

#### Scenario: Non-gendered item excluded from GAS
- **WHEN** selected item has gender = 'unisex' or NULL
- **THEN** that selection is excluded from both numerator and denominator (not counted either way)

### Requirement: Statistical significance in notebook
The analysis notebook SHALL compute a Chi-square test comparing GAS distributions between `gender_hint_enabled = TRUE` and `FALSE` groups per mode.

#### Scenario: p-value is reported for each mode
- **WHEN** notebook runs gender A/B analysis
- **THEN** Chi-square statistic and p-value are printed per mode, with effect size (Cliff's delta) alongside

#### Scenario: Insufficient sample produces warning
- **WHEN** either gender_hint group has fewer than 15 sessions
- **THEN** notebook prints a warning that results are not statistically reliable
