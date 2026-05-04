# Agent Handoff Prompt — Price Intent Aware Recommendation

## Situation

You are working on a **high-risk, deadline-constrained** thesis system update.
The team needs product pricing support and price-intent-aware recommendations, but must avoid destabilizing the current system before report submission.

This change is already proposed and planned at:
- `openspec/changes/add-risk-managed-product-pricing/proposal.md`
- `openspec/changes/add-risk-managed-product-pricing/design.md`
- `openspec/changes/add-risk-managed-product-pricing/tasks.md`
- `openspec/changes/add-risk-managed-product-pricing/specs/price-intent-aware-recommendation/spec.md`

## Mission

Implement or evaluate price-intent-aware recommendation behavior safely:
- Detect budget vs premium user intent
- Apply price as a **secondary** ranking signal (after relevance)
- Keep graceful fallback when price data is missing
- Preserve existing behavior for non-price flows

## Critical Constraints

1. **No big-bang rollout.** Use phased rollout only.
2. **Backward compatibility is mandatory.** Price fields are optional during transition.
3. **Stability over feature completeness.** If trade-offs arise, protect current Path1/Path2 user journeys.
4. **Consistency is mandatory.** Never use per-request random pricing; persisted per-item price only.
5. **Report integrity matters.** Do not mix pre-pricing and post-pricing analytics without explicit separation.

## Required Behavioral Rules

- Relevance retrieval remains primary.
- Price-aware reranking activates only when explicit price intent is detected.
- If `price_cents` is unavailable, silently degrade to relevance-only behavior.
- Response text should explain budget/premium prioritization only when price intent is explicit.

## Risk Focus Areas

- Intent false positives causing unintended price filtering
- Recall drop from overly aggressive price constraints
- Inconsistent user experience if some products lack price
- Analytics drift if rollout gates are skipped

## Execution Priority Order

1. Confirm schema/data readiness for price availability
2. Add/verify intent extraction for budget/premium signals
3. Add ranking overlay with guarded fallback
4. Validate no regression in existing non-price flows
5. Document scope and evaluation boundaries for thesis evidence

## Definition of Done (for this capability)

- Budget and premium intents are detected in multilingual user messages
- Price-aware reranking is applied only when intended
- Missing-price scenarios do not fail requests
- Existing recommendation workflows remain functional and stable
- Behavior is documented clearly for thesis/report interpretation
