## Context

The chat stack currently supports multiple session-selected models (Gemini, GPT-4o, Claude) and a mixed orchestration strategy (direct and agentic). This creates divergent execution paths between frontend model selection, backend validation, orchestration routing, and LLM client construction. Recent runtime failures during intent classification show that chat still depends on Gemini in core flow, even when non-Gemini models are selected.

## Goals / Non-Goals

**Goals:**
- Enforce a single model choice (`gemini-2.5-flash`) across the product.
- Remove agentic orchestration so all requests use direct mode only.
- Align FE and BE behavior so users cannot select unsupported models.
- Reduce branching in orchestration/client factories to simplify operations.

**Non-Goals:**
- Changing retrieval/search logic or recommendation quality behavior.
- Reworking analytics schema beyond fields directly tied to removed modes/models.
- Adding new model providers or introducing fallback provider logic.

## Decisions

1. **Session model is fixed to Gemini (`gemini-2.5-flash`)**
   - **Why:** Prevents incompatible runtime states and keeps one tested execution path.
   - **Alternative considered:** Keep multi-model selection with stricter guards. Rejected due to continued complexity and higher maintenance risk.

2. **Agentic orchestration path is removed from chat streaming flow**
   - **Why:** User requirement is single-agent execution only; direct mode is simpler and already integrated.
   - **Alternative considered:** Keep agentic code but disable by config flag. Rejected to avoid dead-path drift and accidental reactivation.

3. **Frontend model selector UI is reduced to one option**
   - **Why:** Prevents users from submitting unsupported model identifiers.
   - **Alternative considered:** Keep UI choices but map all to Gemini internally. Rejected as misleading UX.

4. **Backend validation accepts only one `preferred_model` value**
   - **Why:** Enforces contract at API boundary and prevents invalid session state from other clients.
   - **Alternative considered:** Auto-coerce unknown models to Gemini. Rejected because silent coercion hides client integration errors.

## Risks / Trade-offs

- **[Risk]** Legacy clients may still submit GPT/Claude values and fail validation  
  → **Mitigation:** Return explicit validation errors and document the new accepted value.
- **[Trade-off]** Removes experimentation flexibility with multiple providers  
  → **Mitigation:** Keep changes isolated so future reintroduction can be done via a separate proposal.
- **[Risk]** Analytics/report queries expecting multi-mode labels may become stale  
  → **Mitigation:** Preserve field presence where possible and standardize emitted mode as `direct`.

## Migration Plan

1. Update FE registration flow to only submit Gemini model.
2. Update BE session model validation and defaults to Gemini-only.
3. Remove/disable agentic routing branch and force direct orchestration mode.
4. Clean up model client selection for removed providers.
5. Execute a dedicated testing stage (frontend validation, backend API checks, stream regression, end-to-end smoke).
6. Update relevant docs/tests and finalize rollout checks.

Rollback approach: restore prior model validation list and orchestration branch in a dedicated revert change if required.

## Open Questions

- Should historical sessions created with GPT/Claude remain readable as-is for analytics, or be normalized when queried?
- Should API return a custom error code/message for deprecated models to aid old clients during transition?
