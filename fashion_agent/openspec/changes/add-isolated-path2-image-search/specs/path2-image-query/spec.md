## ADDED Requirements

### Requirement: PATH 2 image query endpoint
The system SHALL provide a dedicated PATH 2 endpoint for image-to-image retrieval that is separate from existing PATH 1 text-search/chat endpoints.

#### Scenario: Client submits valid PATH 2 image query
- **WHEN** a client sends a PATH 2 request to the image-query endpoint with a valid payload
- **THEN** the system returns ranked visually similar products from the PATH 2 pipeline

### Requirement: PNG validation for PATH 2 input
The PATH 2 endpoint SHALL enforce PNG file validation and return explicit validation errors for unsupported file types.

#### Scenario: Unsupported file type is uploaded
- **WHEN** a client uploads a non-PNG file to the PATH 2 endpoint
- **THEN** the system rejects the request with a validation error that states PNG is required

### Requirement: PATH 2 retrieval isolation
PATH 2 retrieval execution SHALL use its own module/function path and SHALL NOT alter PATH 1 search orchestration or ranking logic.

#### Scenario: PATH 2 request is processed
- **WHEN** a PATH 2 image query is executed
- **THEN** PATH 1 `search()` behavior and outputs remain governed by PATH 1 logic only

### Requirement: PATH 2 feature flag control
The system SHALL allow PATH 2 enablement/disablement via configuration without redeploying PATH 1 behavior changes.

#### Scenario: PATH 2 is disabled
- **WHEN** the PATH 2 feature flag is off
- **THEN** PATH 2 endpoint access is blocked or returns a controlled unavailable response while PATH 1 remains fully operational
