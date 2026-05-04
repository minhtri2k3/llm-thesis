## ADDED Requirements

### Requirement: Backward-Compatible Price Contract
The system SHALL support backward-compatible operation while pricing is being rolled out.

#### Scenario: Legacy consumer reads product payload
- **WHEN** a consumer does not depend on price fields
- **THEN** product retrieval continues without contract breakage during and after rollout

#### Scenario: Partial pricing availability
- **WHEN** some products contain `price_cents` and others do not
- **THEN** API and agent workflows remain functional
- **AND** missing price is handled as a valid transitional state

### Requirement: Phased Rollout Gatekeeping
The system SHALL enforce phased rollout sequencing for pricing-related data and behavior changes.

#### Scenario: Price-aware ranking remains disabled before data readiness
- **WHEN** backfill and payload propagation are incomplete
- **THEN** price-aware ranking is not enabled for production traffic

#### Scenario: Price-aware ranking enabled after readiness
- **WHEN** rollout readiness criteria are met
- **THEN** price-aware ranking can be enabled without requiring schema-breaking changes

### Requirement: Safe Degradation and Rollback
The system SHALL provide safe degradation to relevance-only recommendation behavior if pricing components fail.

#### Scenario: Pricing component failure
- **WHEN** pricing policy lookup or price-aware overlay fails at runtime
- **THEN** the system returns relevance-based recommendations
- **AND** request handling does not fail solely due to pricing logic

#### Scenario: Operational rollback
- **WHEN** price-aware behavior is rolled back
- **THEN** existing schema additions remain non-destructive
- **AND** user-facing recommendation flow continues in non-price mode
