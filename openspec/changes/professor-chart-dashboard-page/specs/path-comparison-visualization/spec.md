## ADDED Requirements

### Requirement: PATH comparison charts with funnel metrics
The system SHALL render comparative PATH 1 and PATH 2 charts using funnel-derived metrics from analytics responses.

#### Scenario: Path comparison data returned
- **WHEN** the analytics response contains path comparison segments for `path1` and `path2`
- **THEN** the UI SHALL render comparative chart series for core metrics including impressions, clicks, cart adds, and conversion-related rates

#### Scenario: One path has no activity
- **WHEN** one path has zero-valued metrics in the selected dataset
- **THEN** the chart SHALL still render both paths and represent zero-valued series explicitly

### Requirement: Integrity status SHALL be visible in path visualizations
Each path comparison section SHALL include data integrity status and issue indicators so invalid data is not interpreted as fully trustworthy.

#### Scenario: Integrity is valid
- **WHEN** a path segment has `integrity.valid=true`
- **THEN** the UI SHALL display the segment as valid without warning indicators

#### Scenario: Integrity is invalid
- **WHEN** a path segment has `integrity.valid=false` or integrity issue counts are non-zero
- **THEN** the UI SHALL display a visible warning state with machine-readable issue labels

### Requirement: Aggregate integrity summary for thesis interpretation
The system SHALL display aggregate integrity summary information near comparative charts.

#### Scenario: Aggregate integrity payload present
- **WHEN** analytics includes aggregate invalid-session or issue-count fields
- **THEN** the page SHALL render a summary row showing invalid session count and top issue categories

#### Scenario: Integrity fields absent
- **WHEN** expected aggregate integrity fields are absent from the response
- **THEN** the page SHALL display a fallback notice that integrity details are unavailable
