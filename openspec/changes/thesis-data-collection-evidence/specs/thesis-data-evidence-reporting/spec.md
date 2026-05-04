## ADDED Requirements

### Requirement: Thesis SHALL define data sources and collection boundaries
The thesis SHALL explicitly state which data sources are used for evidence reporting, including table/log names, session/time boundaries, and inclusion/exclusion criteria.

#### Scenario: Reader audits the evidence scope
- **WHEN** a reader reviews the evidence section
- **THEN** the thesis clearly identifies data provenance and analysis boundaries without ambiguity

### Requirement: Thesis SHALL report token usage with reproducible definitions
The thesis SHALL report LLM token metrics with reproducible definitions for input tokens, output tokens, and total tokens, including both per-session and aggregate summaries.

#### Scenario: Reader validates token metrics
- **WHEN** token usage numbers are presented
- **THEN** each number is traceable to a defined aggregation method and stated cohort

### Requirement: Thesis SHALL report add-to-cart behavior metrics
The thesis SHALL include user behavior evidence focused on add-to-cart signals, with defined counts/rates and denominator definitions for interpretation.

#### Scenario: Reader evaluates behavioral evidence
- **WHEN** add-to-cart analytics are shown
- **THEN** the thesis provides sufficient definitions to determine what user engagement claim is supported

### Requirement: Thesis SHALL report system accuracy evidence
The thesis SHALL present system accuracy using project-approved evaluation metrics and SHALL include sample size/context for each reported value.

#### Scenario: Reader assesses model quality claims
- **WHEN** accuracy claims are made
- **THEN** the thesis pairs each claim with metric values and the evaluation context used to compute them

### Requirement: Thesis SHALL include data quality and validity checks
The thesis SHALL document data quality checks (for example missingness, inconsistency, duplicates, or imbalance) and SHALL state how detected issues affect confidence in conclusions.

#### Scenario: Reader judges whether data is right or wrong
- **WHEN** data quality findings are reviewed
- **THEN** the thesis explains both detected issues and their impact on result trustworthiness

### Requirement: Thesis conclusion SHALL map claims to evidence strength
The final conclusion SHALL classify major claims by evidence strength (supported, partially supported, or inconclusive) and SHALL include explicit limitation statements for weak evidence areas.

#### Scenario: Reader verifies conclusion rigor
- **WHEN** the final conclusion is read
- **THEN** each major claim is linked to concrete evidence and bounded by stated limitations
