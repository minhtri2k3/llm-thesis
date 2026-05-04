## Why

The thesis report is near submission, so introducing pricing now must be done with strict risk control. The current system has no product price field, and adding it affects data storage, retrieval payloads, agent behavior, UI rendering, analytics interpretation, and report consistency.

## What Changes

- Introduce category-based product pricing with market-informed baselines and controlled bounded variation, persisted as stable per-item values.
- Add price-awareness to recommendation behavior so the agent can respond when users ask for cheaper or more premium options.
- Define a phased rollout path that preserves current system stability (schema-safe migration, backward-compatible API fields, and fallback behavior when price is absent).
- Update thesis/report workflow guidance so pricing claims and evaluation evidence remain aligned with the implemented behavior.

## Capabilities

### New Capabilities
- `product-pricing-data`: Define how price is represented, generated, persisted, and propagated through catalog/index/search/cart flows.
- `price-intent-aware-recommendation`: Define price-intent extraction and how ranking/suggestion behavior changes for budget vs premium requests.
- `pricing-rollout-safety`: Define migration, compatibility, validation, and rollback requirements for a low-risk deployment under deadline pressure.

### Modified Capabilities
- None.

## Impact

- Affected systems: PostgreSQL catalog + selection tables, Qdrant payload shape, API response contracts, agent intent/slot logic, frontend product/cart rendering, and analytics interpretation.
- Affected workflows: indexing/backfill pipeline, release sequencing, and thesis documentation alignment.
- Risk profile: medium-to-high if done as one big-bang rollout; reduced with phased, compatibility-first execution.
