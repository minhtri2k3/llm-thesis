## 1. Telemetry Contract and Schema

- [x] 1.1 Define the canonical event contract fields (`session_id`, `path_mode`, event timestamp, and required entity keys) for all funnel events.
- [x] 1.2 Add/adjust database schema to persist `path_mode` (and any required path-scoped context) for impressions, clicks, selections, intents, and orders.
- [x] 1.3 Add compatibility query/view updates so existing analytics consumers continue to function during migration.

## 2. Backend Instrumentation for PATH 1 and PATH 2

- [x] 2.1 Ensure PATH 1 product delivery flow emits contract-complete impression records.
- [x] 2.2 Add PATH 2 impression logging in `/api/path2/image-search` using returned ranked products and session context.
- [x] 2.3 Implement path-scoped result context so selection confirmation resolves against the originating path result set.
- [x] 2.4 Ensure click/intent/order writes preserve correct `path_mode` attribution through the full funnel.

## 3. Frontend Event Wiring Reliability

- [x] 3.1 Ensure chat provider session wiring is initialized before any telemetry fire-and-forget calls.
- [x] 3.2 Update PATH 2 client flow to send required telemetry context fields for downstream funnel events.
- [x] 3.3 Add non-disruptive client-side diagnostics/logging for telemetry call failures to avoid silent data loss.

## 4. Integrity Gates and Analytics Outputs

- [x] 4.1 Implement integrity checks for event coverage and consistency (including upstream/downstream funnel relationships).
- [x] 4.2 Extend behavior analytics responses with path-segmented metrics and machine-readable integrity status.
- [x] 4.3 Add failure-reason reporting so invalid telemetry windows/sessions are explicitly marked non-actionable.

## 5. Test Coverage and Release Safeguards

- [x] 5.1 Add backend tests for path attribution and PATH 2 telemetry capture contracts.
- [x] 5.2 Add tests for selection-context isolation between PATH 1 and PATH 2.
- [x] 5.3 Add analytics invariant tests that fail on integrity regressions.
- [x] 5.4 Run end-to-end verification scenarios for PATH 1-only, PATH 2-only, and mixed-path sessions.
