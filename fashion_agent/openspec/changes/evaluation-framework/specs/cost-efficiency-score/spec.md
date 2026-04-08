## ADDED Requirements

### Requirement: Cost-Efficiency Score definition
The system SHALL define Cost-Efficiency Score (CES) as `BehaviourAccuracy / AvgCostPerTurn_USD` where BehaviourAccuracy is a weighted composite of normalized SR, SCR, and inverse QRR.

#### Scenario: Higher CES indicates better quality per dollar
- **WHEN** Mode A has BehaviourAccuracy = 0.65 and AvgCost = $0.001
- **THEN** CES(A) = 650 — higher than Mode C with BehaviourAccuracy = 0.70 and AvgCost = $0.05 (CES = 14)

#### Scenario: CES is computed in the analysis notebook, not the API
- **WHEN** researcher runs the analysis notebook
- **THEN** CES is calculated from raw API response values using the formula, not returned directly by any endpoint

### Requirement: Normalization before composition
The BehaviourAccuracy composite SHALL normalize each component signal to [0, 1] across all modes before applying weights (SR: 0.40, SCR: 0.30, inverse QRR: 0.20, GAS: 0.10).

#### Scenario: Mode with highest SR gets normalized SR = 1.0
- **WHEN** Mode B has SR = 0.70, Mode A has SR = 0.55, Mode C has SR = 0.50
- **THEN** normalized SR values are [B: 1.0, A: 0.25, C: 0.0] (min-max normalization)

#### Scenario: Weight sensitivity analysis can be performed
- **WHEN** researcher changes SR weight from 0.40 to 0.50 in notebook
- **THEN** CES rankings can be recalculated without any backend changes

### Requirement: CES comparison chart
The analysis notebook SHALL produce a horizontal bar chart comparing CES across all three modes.

#### Scenario: Chart is reproducible from source data
- **WHEN** notebook is run from scratch with a fresh DB connection
- **THEN** the CES chart is produced without manual input
