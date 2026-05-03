## ADDED Requirements

### Requirement: Dedicated professor analytics page
The system SHALL provide a dedicated professor analytics page as a separate route, distinct from the register dialog flow.

#### Scenario: Navigate to professor page after successful unlock
- **WHEN** a user taps "Professor View", enters a valid access code, and unlock succeeds
- **THEN** the application SHALL navigate to the dedicated professor analytics page route

#### Scenario: Professor page uses full-page layout
- **WHEN** the professor analytics page is opened
- **THEN** the UI SHALL render analytics content in a full-page layout optimized for chart readability

### Requirement: Professor page SHALL show chart-first thesis summary
The professor analytics page SHALL present thesis metrics as chart-first sections with supporting KPI summaries.

#### Scenario: Data available for visualization
- **WHEN** analytics data loads successfully
- **THEN** the page SHALL show chart sections and summary cards for path comparison and token usage

#### Scenario: No analytics data available
- **WHEN** analytics endpoints return empty datasets
- **THEN** the page SHALL show an explicit empty state message instead of blank chart containers

### Requirement: Professor page SHALL preserve protected access behavior
Professor analytics access SHALL remain protected by admin-key validation and must not expose analytics without successful unlock.

#### Scenario: Invalid access code
- **WHEN** a user submits an incorrect professor access code
- **THEN** the system SHALL keep the user out of the professor page and show an access error

#### Scenario: Missing or expired access context
- **WHEN** professor page initialization occurs without a valid access context
- **THEN** the system SHALL redirect back to the unlock flow or register entry point
