## 1. Frontend model de-scope

- [x] 1.1 Remove GPT-4o and Claude model options from `clothie_web/lib/screens/register_screen.dart`
- [x] 1.2 Ensure session creation always submits `preferred_model = "gemini-2.5-flash"`
- [x] 1.3 Update any frontend labels/text that imply multi-model support

## 2. Backend session model enforcement

- [x] 2.1 Restrict `CreateSessionRequest.preferred_model` validation to Gemini-only in `fashion_agent/api/main.py`
- [x] 2.2 Keep validation error messaging explicit for deprecated model values
- [x] 2.3 Verify default `preferred_model` remains `gemini-2.5-flash` across session creation paths

## 3. Remove agentic orchestration path

- [x] 3.1 Update orchestration mode helper to return direct mode only
- [x] 3.2 Remove/disable agentic branch in `chat_stream` so no `agentic_start/agentic_done` flow is used
- [x] 3.3 Ensure completion metadata emits direct mode semantics consistently

## 4. Simplify model client routing and dead code

- [x] 4.1 Remove GPT/Claude client selection branches from `fashion_agent/shared/llm.py` if unreachable
- [x] 4.2 Remove unused imports/usages tied to agentic orchestrator and deprecated providers
- [x] 4.3 Update documentation/comments that describe multi-provider and agentic behavior

## 5. Testing stage

- [x] 5.1 Run frontend validation for registration/chat flow with Gemini-only model option
- [x] 5.2 Run backend API tests for `/api/sessions` model validation (accept Gemini, reject GPT/Claude)
- [x] 5.3 Run chat stream regression test to confirm no agentic path is invoked
- [x] 5.4 Run end-to-end smoke test through FE → BE to confirm stable response completion

## 6. Validation and sign-off

- [x] 6.1 Verify completion metadata/logging still reports direct-mode semantics
- [x] 6.2 Verify docs/comments no longer describe GPT/Claude or agentic runtime as active behavior
