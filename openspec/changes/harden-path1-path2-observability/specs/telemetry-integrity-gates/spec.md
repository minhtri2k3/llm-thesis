## ADDED Requirements

### Requirement: Telemetry integrity gate computation
The system SHALL compute integrity gates that indicate whether behavioral telemetry is sufficiently complete and consistent for analysis.

#### Scenario: Missing required event class
- **WHEN** a session has downstream events (for example, clicks or intents) without required upstream coverage (for example, impressions) beyond allowed exceptions
- **THEN** the integrity gate SHALL mark that session/data window as invalid with explicit failure reasons

#### Scenario: Contract-complete session
- **WHEN** a session satisfies required event coverage and consistency checks
- **THEN** the integrity gate SHALL mark that session/data window as valid for analysis

### Requirement: Integrity-aware analytics responses
Analytics endpoints SHALL return integrity status and supporting diagnostics alongside funnel metrics.

#### Scenario: Path-level funnel analytics
- **WHEN** clients request behavioral funnel analytics
- **THEN** the response SHALL include path-segmented metrics and integrity status fields for each segment

#### Scenario: Invalid data visibility
- **WHEN** integrity checks fail for returned data
- **THEN** analytics responses SHALL include machine-readable failure reasons so consumers can avoid drawing conclusions from invalid data

### Requirement: Regression protection for telemetry contracts
The system SHALL include automated tests that fail when path attribution or integrity rules regress.

#### Scenario: Path attribution regression
- **WHEN** a telemetry-producing flow omits required path attribution fields
- **THEN** automated contract tests SHALL fail

#### Scenario: Integrity invariant regression
- **WHEN** core funnel invariants are violated in tested flows
- **THEN** automated integrity tests SHALL fail and identify the violated invariant
