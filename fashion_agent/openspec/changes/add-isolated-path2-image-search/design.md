## Context

The current production flow is PATH 1: text query -> intent + retrieval orchestration -> hybrid search pipeline.  
PATH 2 must introduce image-to-image retrieval while preserving existing PATH 1 quality and uptime.  
The codebase already has FashionSigLIP image embedding support and Qdrant image vectors, which enables PATH 2 without reworking PATH 1 internals.

## Goals / Non-Goals

**Goals:**
- Add PATH 2 as a fully separate search path with dedicated API and retrieval module.
- Enforce upload validation and predictable error handling for PATH 2 requests.
- Ensure PATH 1 API contracts and behavior are unchanged before/after PATH 2 rollout.
- Support safe rollout via feature flag and explicit observability.

**Non-Goals:**
- Refactoring PATH 1 retrieval ranking or orchestration logic.
- Re-indexing the catalog or replacing embedding models.
- Implementing virtual try-on or cross-modal generation in this change.

## Decisions

1. **Separate endpoint and handler for PATH 2**
   - Decision: Add a dedicated image-query endpoint (separate from chat stream and PATH 1 text search entry points).
   - Rationale: Prevent contract coupling and accidental behavior drift in PATH 1.
   - Alternative considered: Extend existing chat endpoint payload with image input; rejected due to high regression risk.

2. **Separate PATH 2 retrieval module**
   - Decision: Implement PATH 2 retrieval in a new module/function path, independent from PATH 1 `search()` orchestration.
   - Rationale: Hard isolation boundary and easier rollback.
   - Alternative considered: Branching logic inside existing `search()`; rejected because shared code changes increase blast radius.

3. **PNG-first upload policy**
   - Decision: PATH 2 accepts PNG query files for initial rollout and rejects non-compliant input with clear validation errors.
   - Rationale: Simplifies first release policy and reduces ambiguity in client handling.
   - Alternative considered: Allow JPG/JPEG/WEBP immediately; deferred to later expansion after stable PATH 2 baseline.

4. **Feature-flagged rollout**
   - Decision: Gate PATH 2 endpoint/UI with an explicit flag.
   - Rationale: Allows enabling PATH 2 gradually and disabling quickly without affecting PATH 1.
   - Alternative considered: Always-on rollout; rejected due to operational risk.

5. **PATH 1 regression guardrail**
   - Decision: Add explicit regression checks for PATH 1 endpoint behavior and retrieval expectations as part of PATH 2 delivery.
   - Rationale: Isolation must be verifiable, not assumed.
   - Alternative considered: Rely on manual validation only; rejected due to insufficient confidence.

## Risks / Trade-offs

- **[Risk] PATH 2 code accidentally imports/modifies PATH 1 logic** -> **Mitigation:** Separate module boundary + code review checklist + regression tests.
- **[Risk] PNG-only policy increases user friction** -> **Mitigation:** Return explicit error guidance and plan broadened format support as follow-up.
- **[Risk] Additional GPU/CPU load from image queries** -> **Mitigation:** Keep PATH 2 separately rate-limited and monitor latency independently.
- **[Risk] Feature flag drift between API/UI** -> **Mitigation:** Centralized config and startup-time validation logs.

## Migration Plan

1. Merge code with PATH 2 disabled by default.
2. Deploy and run PATH 1 regression suite in production-like environment.
3. Enable PATH 2 for controlled testing cohort.
4. Monitor PATH 2 latency/error rate and PATH 1 stability metrics in parallel.
5. Roll back by disabling PATH 2 flag if any risk threshold is crossed.

## Open Questions

- Should PNG-only remain long-term, or expand to JPG/JPEG/WEBP after MVP stabilization?
- Is PATH 2 exposed in chat-first UX, or only via explicit “Search by image” entry point initially?
- Do we need a separate PATH 2 result fusion strategy (pure image similarity vs composed image+text) in v1?
