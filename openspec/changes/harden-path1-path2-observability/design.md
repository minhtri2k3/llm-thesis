## Context

PATH 1 (chat/SSE flow) and PATH 2 (image-to-image flow) are both available, but current telemetry does not produce a reliable evaluation dataset. The current behavior tracking stack is split across frontend fire-and-forget calls and backend event writes, with inconsistent coverage between paths.

Known pain points:
- PATH 1 impression logging depends on frontend session state wiring that can be skipped.
- PATH 2 returns products but does not participate in the same funnel instrumentation as PATH 1.
- Event tables do not encode `path_mode`, so analytics cannot compare PATH 1 versus PATH 2.
- Existing analytics cannot clearly indicate when data quality is too weak for conclusions.

Stakeholders:
- Thesis evaluator (needs defensible, path-level evidence).
- Product team (needs trustworthy funnel insights).
- Engineering team (needs clear instrumentation contracts and test gates).

## Goals / Non-Goals

**Goals:**
- Define one telemetry contract that both PATH 1 and PATH 2 MUST follow.
- Ensure all funnel stages are captured with explicit `path_mode` attribution.
- Add integrity gates so analytics can declare data as valid/invalid for interpretation.
- Keep the solution compatible with existing flows and progressive rollout.

**Non-Goals:**
- Changing recommendation quality/ranking algorithms.
- Adding real payment processing.
- Redesigning UI/UX beyond telemetry-triggering interactions.
- Historical backfill of all legacy sessions before this change.

## Decisions

1. **Adopt a path-attributed event schema for all funnel events.**  
   Every behavioral event write SHALL include `session_id`, `image_id` (if applicable), `path_mode`, and event timestamp.  
   **Rationale:** Without path attribution and stable keys, cross-path analysis is not defensible.

2. **Instrument impressions for PATH 1 and PATH 2 at the source of product delivery.**  
   PATH 1 impression emission SHALL be tied to product payload delivery in the chat flow, and PATH 2 SHALL log impressions when `/api/path2/image-search` returns ranked products.  
   **Alternative considered:** frontend-only logging for all impressions.  
   **Why rejected:** best-effort frontend logging can silently miss events due to state or network issues.

3. **Separate selection context by path.**  
   Selection confirmation SHALL use path-aware result context so PATH 2 selections cannot depend on PATH 1 cached results.  
   **Alternative considered:** single shared cache for all search modes.  
   **Why rejected:** cross-path cache coupling creates selection mismatches and corrupts funnel attribution.

4. **Add telemetry integrity gates as first-class analytics outputs.**  
   Analytics SHALL compute integrity checks (coverage and consistency) and return gate status with reasons, not just raw funnel counts.  
   **Rationale:** teams need machine-readable confidence before acting on metrics.

5. **Enforce contract behavior with automated tests.**  
   Tests SHALL validate path attribution, event coverage by path, and core invariants (for example, sessions with clicks should also have impressions unless explicitly exempted).  
   **Rationale:** prevent regressions that silently degrade dataset quality.

## Risks / Trade-offs

- **[Risk] Increased write volume from broader impression logging** → **Mitigation:** batch writes where possible, index by session/time/path, and monitor DB latency.
- **[Risk] Mixed old/new sessions during rollout may skew analytics** → **Mitigation:** integrity gates classify sessions/data windows by schema completeness.
- **[Risk] Frontend and backend event duplication** → **Mitigation:** define source-of-truth per event type and use idempotency keys where needed.
- **[Risk] Additional schema fields complicate existing queries** → **Mitigation:** provide compatibility views and phased query migration.

## Migration Plan

1. Add schema changes for path attribution and any path-scoped context tables/fields.
2. Deploy backend instrumentation for PATH 2 impression and path-aware selection handling.
3. Update PATH 1 frontend session propagation and telemetry calls to satisfy contract fields.
4. Enable integrity-gate analytics output and expose status in funnel endpoints.
5. Run contract/invariant test suite and compare PATH 1/PATH 2 sample sessions.
6. Roll out to production with integrity monitoring; treat invalid gates as non-actionable data.

## Open Questions

- Should path attribution be modeled as enum (`path1`, `path2`) or extensible string for future modes?
- What minimum data threshold (sessions/events) is required before analytics are considered publishable for thesis reporting?
- Should integrity gate failures block dashboard display or only show warnings with confidence labels?
