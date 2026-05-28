# Spec: react-agent

## Overview

`agent/react_agent.py` is a self-contained ReAct pipeline module. It provides `chat()` and `chat_stream()` with the same external signature as `fashion_agent`, making it a drop-in alternative at the routing layer. It shares no in-memory state with `fashion_agent.py`.

## Interface

```python
def chat(
    message: str,
    session_id: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> AgentResponse: ...

def chat_stream(
    message: str,
    session_id: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> Generator[Union[ThinkingEvent, SynthesisChunk], None, None]: ...
```

## Execution Flow

```
chat_stream(message, session_id)
  │
  ├─ 1. get_history(session_id)
  ├─ 2. classify_intent(message, history)   → ClassifiedIntent
  │     yield ThinkingEvent("classify_done", ...)
  │
  ├─ 3. _react_gate(classified)
  │     ├─ False → skip to step 6 with products=[]
  │     └─ True  → step 4
  │
  ├─ 4. orchestrate_with_gemini(
  │         query=classified.refined_query,
  │         history_text=...,
  │         gender=...,
  │         max_iterations=4,
  │     )   → AgenticOrchestrationResult
  │     yield ThinkingEvent("search_done", f"{len(result.products)} products found")
  │
  ├─ 5. _log_react_traces(session_id, message, result)
  │
  ├─ 6. _build_synthesis_context(message, products, history, ...)
  ├─ 7. stream synthesis via get_client().stream(STREAM_SYNTHESIS_PROMPT)
  │     yield ResponseToken / ThinkingToken / TokenUsage chunks
  │
  └─ 8. add_message(), log_token_usage(
             orchestration_mode="react",
             response_latency_ms=elapsed,
             llm_call_count=len(result.tool_calls) + 2,  # classify + synthesis
         )
         yield ThinkingEvent("done", ...)
```

## Constants

```python
REACT_CONFIDENCE_THRESHOLD = float(os.getenv("REACT_CONFIDENCE_THRESHOLD", "0.50"))
```

## Gate Logic

```python
def _react_gate(classified: ClassifiedIntent) -> bool:
    if classified.intent in ("out_of_scope", "unclear"):
        return False
    if classified.confidence < REACT_CONFIDENCE_THRESHOLD:
        return False
    return True
```

## Trace Logging

```python
def _log_react_traces(session_id: str, query_text: str, result: AgenticOrchestrationResult) -> None:
    # One INSERT per tool call in result.tool_calls
    # Uses batch INSERT for efficiency
    # Non-fatal: errors are logged but do not raise
```

## Intentional Differences from `fashion_agent.py`

| Aspect | Direct (`fashion_agent.py`) | ReAct (`react_agent.py`) |
|---|---|---|
| Slot accumulation | ✅ TTLCache per session | ❌ None — stateless per turn |
| Clarification gate | ✅ `check_clarification()` | ❌ None — LLM decides |
| Search | Deterministic hybrid search | Gemini tool-calling loop |
| Multi-turn memory | Slot merge across turns | In-context history only |
| Max LLM calls | 2 (classify + synthesize) | 2 + N iterations (N ≤ 4) |

## No-op on Out-of-Scope

When `_react_gate()` returns False, `react_agent` still synthesizes a response using the LLM — it just does so with `products=[]` and `tool_results_text=""`. This matches the Direct pipeline's behavior on `out_of_scope` intents (a polite decline with no search results).
