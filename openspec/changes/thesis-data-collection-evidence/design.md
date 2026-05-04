## Context

The thesis document currently explains system architecture and implementation, but readers lack a dedicated evidence narrative that shows how collected data supports the final claims. The project already records analytics in PostgreSQL (for token usage and user behavior) and has evaluation outputs for search/assistant quality. The design must convert these existing signals into a transparent, reproducible thesis section without introducing new production instrumentation.

## Goals / Non-Goals

**Goals:**
- Define a clear data evidence structure in the thesis for token usage, add-to-cart behavior, and system accuracy.
- Standardize metric definitions, aggregation logic, and reporting format so results are auditable.
- Add validity checks so readers can judge whether the dataset is trustworthy and where conclusions are limited.
- Add a conclusion framework that ties each claim to measured evidence and explicitly states uncertainty.

**Non-Goals:**
- Implementing new backend logging tables or new telemetry pipelines.
- Redesigning the analytics API/dashboard UI.
- Re-running large-scale experiments beyond existing collected data.
- Changing the product retrieval algorithm as part of this documentation change.

## Decisions

### D1 — Use existing analytics sources as the canonical evidence base
The thesis will reference existing stored data (e.g., `llm_token_usage`, behavior/event tables, and evaluation outputs) rather than introducing ad-hoc manual counting.

**Rationale:** This keeps evidence reproducible and aligned with actual system operation.

**Alternative considered:** Manual spreadsheet summaries compiled from screenshots. Rejected because they are hard to verify and prone to transcription error.

### D2 — Report each metric with explicit numerator, denominator, and cohort boundaries
Each reported value will include definition and scope (time/session range, inclusion criteria, exclusions).

**Rationale:** Prevents ambiguous interpretation (for example, total tokens across all sessions vs. per-session average).

**Alternative considered:** Presenting only high-level percentages. Rejected because percentages without counts or cohort boundaries are not auditable.

### D3 — Add a dedicated “Data Quality and Validity” subsection
The thesis will include checks for missing records, inconsistent labels/events, duplicate sessions, and sample imbalance.

**Rationale:** The user’s core concern is helping readers determine whether data is “right or wrong”; explicit validity checks address this directly.

**Alternative considered:** Folding quality remarks into conclusion only. Rejected because quality checks must be shown before inference.

### D4 — Use claim-to-evidence mapping in the final conclusion
Every final claim will be classified as supported, partially supported, or inconclusive based on available metrics and validity outcomes.

**Rationale:** Improves scientific clarity and prevents over-claiming.

**Alternative considered:** Narrative-only conclusion prose. Rejected because it can hide weak evidence links.

## Risks / Trade-offs

- **Metric mismatch between tables and thesis wording** → Mitigation: define each metric formula in-text and keep table/figure labels aligned with source query semantics.
- **Small or biased sample inflates confidence** → Mitigation: always report sample size and add limitation statements near each key claim.
- **Incomplete logging windows cause undercounting** → Mitigation: document data collection window and exclude partial windows from aggregate conclusions.
- **Reader overload from too many indicators** → Mitigation: keep a compact core metric set and move supplementary details to appendix tables.

## Migration Plan

1. Add a new “Data Collection and Evidence Integrity” subsection in the thesis evaluation chapter.
2. Insert three metric blocks: token usage, add-to-cart behavior, and system accuracy with consistent definitions.
3. Add a “Data Quality and Validity” block describing checks and observed issues.
4. Update the final conclusion section to include claim-to-evidence mapping and limitations.
5. Add appendix references (optional) for full metric tables/query definitions.
6. Rebuild the thesis PDF and verify section references and numbering.

**Rollback strategy:** Revert the thesis section additions and restore the previous evaluation/conclusion narrative if evidence framing is not approved.

## Open Questions

- Which exact accuracy metric set should be treated as primary in the main chapter (e.g., Recall@k, MRR, HitRate@k)?
- What minimum sample size threshold should mark a claim as “supported” versus “inconclusive”?
- Should behavior evidence focus only on add-to-cart events or include downstream intent/order signals in the main text?
