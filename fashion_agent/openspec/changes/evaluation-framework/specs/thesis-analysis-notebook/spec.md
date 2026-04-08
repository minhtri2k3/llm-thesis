## ADDED Requirements

### Requirement: Reproducible analysis notebook
The system SHALL provide `analysis/thesis_evaluation.ipynb` as a reproducible Jupyter notebook that connects to Postgres, fetches data from analytics endpoints or directly from DB views, and produces all thesis charts and statistical results.

#### Scenario: Notebook runs end-to-end without manual input
- **WHEN** researcher runs "Run All Cells" in Jupyter
- **THEN** all cells execute without error, producing charts and statistical summaries

#### Scenario: DB connection is configured via environment variable
- **WHEN** `DATABASE_URL` environment variable is set
- **THEN** notebook connects to the correct Postgres instance without code changes

### Requirement: Statistical tests in notebook
The notebook SHALL include Chi-square, Kruskal-Wallis, and bootstrap confidence interval tests, with Cliff's delta effect size for all comparisons.

#### Scenario: Chi-square test for Selection Rate
- **WHEN** notebook runs SR comparison cell
- **THEN** Chi-square statistic and p-value are printed for SR across all 3 modes

#### Scenario: Kruskal-Wallis test for QRR
- **WHEN** notebook runs QRR comparison cell
- **THEN** Kruskal-Wallis H statistic and p-value are printed across all 3 modes

#### Scenario: Bootstrap CI for CES
- **WHEN** notebook runs CES confidence interval cell with n=1000 bootstrap samples
- **THEN** 95% CI is printed for each mode's CES value

### Requirement: Thesis summary table
The notebook SHALL produce a formatted summary table comparing all metrics across all three modes, readable in both notebook and exported PDF form.

#### Scenario: Summary table contains all five key metrics
- **WHEN** notebook renders the final summary cell
- **THEN** table contains SR(%), SCR(%), QRR, avg_USD_per_turn, and CES for each mode

### Requirement: Dev-only dependencies
The scipy, pandas, matplotlib, and seaborn packages SHALL be listed in `requirements-dev.txt` and NOT in `requirements.txt`.

#### Scenario: Production Docker build excludes analysis deps
- **WHEN** `docker build` runs using `requirements.txt`
- **THEN** scipy, pandas, matplotlib, seaborn are NOT installed in the production image
