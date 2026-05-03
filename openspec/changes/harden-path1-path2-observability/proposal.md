## Why

PATH 1 and PATH 2 currently run, but the behavioral telemetry is not trustworthy enough to prove system quality. Key gaps (missing PATH attribution, incomplete PATH 2 funnel capture, and fragile session/event wiring) prevent reliable conclusions about whether recommendations actually work.

## What Changes

- Establish a single end-to-end telemetry contract for both PATH 1 (chat/SSE) and PATH 2 (image-to-image), with explicit event semantics and required fields.
- Add event attribution so every behavioral event can be analyzed by `path_mode` (`path1` or `path2`).
- Ensure impressions, clicks, selections, intents, and orders are all captured for PATH 1 and PATH 2, not only for the chat flow.
- Add telemetry integrity gates (coverage + consistency checks) so analytics can distinguish “valid dataset” from “incomplete instrumentation.”
- Add analytics outputs for path-level funnel comparisons and integrity status.
- Add automated tests for path telemetry contracts, path attribution, and funnel invariants.

## Capabilities

### New Capabilities
- `path-observability`: Define and enforce complete, path-attributed behavioral tracking across PATH 1 and PATH 2.
- `telemetry-integrity-gates`: Define integrity checks and reporting signals that determine whether collected telemetry is reliable for evaluation.

### Modified Capabilities
- None.

## Impact

- Backend: `fashion_agent/api/main.py`, `fashion_agent/agent/memory.py`, `fashion_agent/agent/fashion_agent.py`.
- Frontend: `clothie_web/lib/providers/chat_provider.dart`, `clothie_web/lib/services/api_service.dart`, `clothie_web/lib/widgets/product_card.dart`, PATH 2 interaction surfaces.
- Database: behavior tables and analytics queries/views for path attribution and integrity metrics.
- Tests: backend API/contract tests and telemetry integrity/funnel tests.
