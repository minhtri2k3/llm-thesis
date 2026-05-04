## Context

The current fashion system does not include product pricing in its catalog, retrieval payloads, agent outputs, or cart snapshot model. Adding pricing is cross-cutting because it affects PostgreSQL schema, index payloads, API contracts, agent intent/ranking behavior, frontend rendering, analytics interpretation, and thesis/report narrative consistency.

The primary constraint is timing: report submission is near-term, so rollout safety and backward compatibility are more important than maximum feature depth. Existing behavior must remain stable for sessions and workflows that do not use pricing.

## Goals / Non-Goals

**Goals:**
- Introduce stable product pricing driven by category-level market baselines.
- Add price-aware recommendation behavior for budget-oriented and premium-oriented user requests.
- Preserve existing system behavior when pricing data is absent or partially available.
- Define a phased rollout and rollback path that minimizes disruption to thesis evidence and live workflows.

**Non-Goals:**
- Building a real-time dynamic pricing engine based on inventory, demand, or user segmentation.
- Reworking all ranking logic beyond the scoped price-intent overlay.
- Re-baselining historical analytics that were collected before price support exists.

## Decisions

1. **Persisted per-item pricing instead of per-request randomization**
   - Decision: Generate price once (during migration/backfill/ingestion) and store it in the database.
   - Rationale: Prevents inconsistent prices across search results, cart, and order flows.
   - Alternatives considered:
     - Per-request random generation: rejected because it causes unstable UX and analytics noise.
     - Fully deterministic hash-only generation: rejected because it does not align with external market baselines.

2. **Category baseline + bounded jitter model**
   - Decision: Use market-informed category baselines and bounded variation bands to generate realistic item prices.
   - Rationale: Produces plausible price distributions while preserving category identity.
   - Alternatives considered:
     - Single fixed price per category: rejected for unrealistic catalog uniformity.
     - Unbounded random price: rejected for high outlier risk and poor trust.

3. **Price intent as an additive ranking signal**
   - Decision: Keep core relevance retrieval intact, then apply price-intent-aware filtering/reranking.
   - Rationale: Maintains retrieval quality and avoids destabilizing existing recommendation behavior.
   - Alternatives considered:
     - Hard filtering before retrieval: rejected due to recall loss.
     - Full ranking rewrite: rejected due to timeline and regression risk.

4. **Backward-compatible contract design**
   - Decision: Make price fields optional during transition and require graceful fallback in API/UI/agent output.
   - Rationale: Supports phased deployment and safe rollback.
   - Alternatives considered:
     - Mandatory price fields immediately: rejected due to migration and availability risk.

5. **Phased release with explicit rollback checkpoints**
   - Decision: Roll out in sequence (schema/backfill → index payload → backend/agent → frontend/documentation).
   - Rationale: Limits blast radius and simplifies issue isolation.
   - Alternatives considered:
     - Big-bang deployment: rejected as too risky under deadline pressure.

## Risks / Trade-offs

- **[Risk]** Price baseline quality differs by category due to uneven external evidence.  
  **Mitigation:** Store baselines as configurable policy data and keep category-level audit notes.

- **[Risk]** Regression in retrieval behavior if price filtering is too aggressive.  
  **Mitigation:** Apply price as a secondary signal with fallback to relevance-first output.

- **[Risk]** Inconsistent results during phased rollout when some items lack price.  
  **Mitigation:** Keep nullable/optional fields with explicit fallback behavior until completion.

- **[Risk]** Thesis metrics interpretation changes after price-aware behavior is enabled.  
  **Mitigation:** Separate pre-pricing vs post-pricing reporting windows and document scope clearly.

## Migration Plan

1. Add schema support for optional price fields and policy table(s).
2. Backfill prices for existing products using category baseline + bounded variation.
3. Rebuild or refresh index payloads to include price where available.
4. Enable backend/agent propagation and price-intent overlay while preserving non-price fallback.
5. Enable frontend rendering for price fields with null-safe behavior.
6. Update report documentation sections that describe data model, workflow, and evaluation boundaries.
7. Promote optional fields to required only after completeness targets are met and validated.

Rollback strategy:
- Disable price-aware ranking switch and continue relevance-only flow.
- Continue serving optional price fields (or omit safely) without breaking existing clients.
- Retain schema additions; avoid destructive rollback of populated pricing columns.

## Open Questions

- Which confidence threshold should trigger price-intent-aware reranking versus a normal relevance response?
- Should category baseline policies be versioned for thesis reproducibility?
- What minimum backfill completeness is required before enabling price display in all user surfaces?
