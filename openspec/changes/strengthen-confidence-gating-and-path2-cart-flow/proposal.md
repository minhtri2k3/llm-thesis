## Why

The current search flow often proceeds to recommendations before collecting enough user intent detail, and the current PATH 2 add-to-cart interaction is brittle because it depends on LLM intent classification and confirm-turn routing. This creates avoidable misfires in both recommendation quality and cart reliability.

## What Changes

- Reintroduce a pre-search readiness gate for search intents so the system asks clarifying questions when confidence is low or required slots are incomplete.
- Apply the readiness gate before executing PATH 1 text/follow-up search queries, instead of waiting for zero-result fallback clarifications.
- Add a dedicated PATH 2 add-to-cart flow that writes selections directly through an API contract, without relying on product-select intent parsing.
- Preserve path attribution (`path_mode`) and telemetry consistency for impressions, clicks, cart adds, and downstream funnel analytics.
- Add focused tests for gating behavior and PATH 2 direct cart insertion success/failure paths.

## Capabilities

### New Capabilities
- `confidence-gated-query-readiness`: Define required confidence and slot-completeness behavior before executing search queries.
- `path2-direct-cart-selection`: Define a dedicated PATH 2 cart-add contract that bypasses conversational selection parsing.

### Modified Capabilities
- None.

## Impact

- Backend orchestration: `fashion_agent/agent/fashion_agent.py`, `fashion_agent/agent/slot_completeness.py`, `fashion_agent/agent/intent_classifier.py`.
- Backend API/data path: `fashion_agent/api/main.py`, `fashion_agent/agent/memory.py`.
- Frontend cart interaction: `clothie_web/lib/widgets/product_card.dart`, `clothie_web/lib/screens/chat/chat_provider.dart`, `clothie_web/lib/services/api_service.dart`.
- Validation coverage: backend path observability and flow tests in `fashion_agent/tests/` and relevant Flutter tests.
