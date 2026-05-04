## Why

The current system mixes multiple model providers (Gemini, GPT-4o, Claude) with agentic orchestration paths, which increases operational complexity and has caused runtime failures in chat flow. We need a stable, single-path architecture that uses one model and one execution mode consistently across frontend and backend.

## What Changes

- Remove GPT-4o and Claude model options from frontend session setup and backend session validation.
- Enforce a single allowed session model (`gemini-2.5-flash`) for all chat sessions.
- Remove agentic orchestration execution paths so chat always runs through the direct agent pipeline.
- Eliminate multi-provider branching logic that is no longer reachable after de-scoping.
- Add a dedicated testing stage covering frontend, backend, and end-to-end validation for the Gemini-only direct flow.
- **BREAKING**: Existing behavior that allowed selecting GPT-4o or Claude is removed.

## Capabilities

### New Capabilities
- `single-agent-runtime`: Enforce one-model (Gemini) and one-mode (direct, non-agentic) execution for all chat requests.

### Modified Capabilities
- None.

## Impact

- Affected frontend files in `clothie_web` that render and send model selection.
- Affected backend files in `fashion_agent` that validate `preferred_model`, route orchestration mode, and construct LLM clients.
- Behavioral impact on API consumers: non-Gemini model selections are no longer accepted.
