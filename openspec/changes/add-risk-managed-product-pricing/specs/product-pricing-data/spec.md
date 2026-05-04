## ADDED Requirements

### Requirement: Stable Product Price Persistence
The system SHALL persist a canonical `price_cents` value per product so the same product has a consistent price across retrieval, cart, and order workflows.

#### Scenario: Existing product receives backfilled price
- **WHEN** a product exists without `price_cents` and backfill is executed
- **THEN** the system stores a non-negative `price_cents` value for that product
- **AND** subsequent reads return the same `price_cents` unless an explicit pricing update is applied

#### Scenario: Product appears in multiple surfaces
- **WHEN** the same product is shown in search results and then added to cart
- **THEN** both surfaces expose the same `price_cents` value

### Requirement: Category Baseline Pricing Policy
The system SHALL generate or update product prices from a category policy that defines baseline and bounded variation constraints.

#### Scenario: Price generated from category policy
- **WHEN** a product with category `C` requires price generation
- **THEN** the system uses policy for category `C` to compute `price_cents`
- **AND** the generated value stays within the configured category bounds

#### Scenario: Missing category policy
- **WHEN** a product category has no configured pricing policy
- **THEN** the system SHALL not generate an out-of-contract price
- **AND** the product remains readable with price treated as unavailable

### Requirement: Price Propagation Through Retrieval Payloads
The system SHALL propagate `price_cents` through indexing and retrieval payloads when available.

#### Scenario: Indexed payload includes price
- **WHEN** a product with `price_cents` is indexed
- **THEN** the corresponding retrieval payload includes `price_cents`

#### Scenario: Price absent in payload
- **WHEN** a product payload lacks `price_cents`
- **THEN** retrieval remains successful
- **AND** downstream consumers receive product data without failure
