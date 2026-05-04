## ADDED Requirements

### Requirement: Price Intent Extraction
The system SHALL detect user price preference intent for budget-seeking and premium-seeking queries.

#### Scenario: Budget intent detected
- **WHEN** a user requests cheaper, budget, or low-cost options
- **THEN** the system classifies the request as budget-oriented price intent

#### Scenario: Premium intent detected
- **WHEN** a user requests expensive, premium, or high-end options
- **THEN** the system classifies the request as premium-oriented price intent

### Requirement: Price-Aware Ranking Overlay
The system SHALL apply price-aware ranking or filtering as a secondary overlay after core relevance retrieval.

#### Scenario: Budget-oriented reranking
- **WHEN** budget price intent is active and price data is available
- **THEN** lower-priced relevant items are prioritized over higher-priced comparable items
- **AND** relevance constraints remain enforced

#### Scenario: Premium-oriented reranking
- **WHEN** premium price intent is active and price data is available
- **THEN** higher-priced relevant items are prioritized over lower-priced comparable items
- **AND** relevance constraints remain enforced

#### Scenario: Price data unavailable
- **WHEN** price intent is active but product price is unavailable
- **THEN** the system falls back to relevance-first behavior without failing the request

### Requirement: Price-Aware Response Transparency
The system SHALL reflect price preference handling in generated recommendations when price intent is explicit.

#### Scenario: Budget explanation in response
- **WHEN** budget price intent is detected and at least one priced item is returned
- **THEN** the response indicates that lower-price options were prioritized

#### Scenario: Premium explanation in response
- **WHEN** premium price intent is detected and at least one priced item is returned
- **THEN** the response indicates that premium options were prioritized
