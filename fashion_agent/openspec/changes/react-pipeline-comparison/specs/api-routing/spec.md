# Spec: api-routing

## Overview

`api/main.py` is the single routing layer that decides which agent module handles a request. The decision is made once per request by reading `orchestration_mode` from the session record.

## `CreateSessionRequest` Changes

```python
class CreateSessionRequest(BaseModel):
    user_name: str = ""
    year_of_birth: Optional[int] = None
    gender: Optional[str] = None
    preferred_model: str = "gemini-2.5-flash"
    orchestration_mode: str = "direct"            # NEW

    def model_post_init(self, __context) -> None:
        # ... existing year/gender/model validation ...
        if self.orchestration_mode not in ("direct", "react"):
            raise ValueError('orchestration_mode must be "direct" or "react"')
```

## `POST /api/sessions` Handler Change

```python
@app.post("/api/sessions")
async def create_session_endpoint(req: CreateSessionRequest):
    session_id = create_session(
        user_name=req.user_name,
        year_of_birth=req.year_of_birth,
        gender=req.gender,
        preferred_model=req.preferred_model,
        orchestration_mode=req.orchestration_mode,    # NEW
    )
    return CreateSessionResponse(session_id=session_id)
```

## `POST /api/chat/stream` Handler Change

```python
from agent import fashion_agent, react_agent          # NEW import
from agent.memory import get_session_orchestration_mode  # NEW import

@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    mode = get_session_orchestration_mode(req.session_id or "")  # NEW — 1 DB read

    if mode == "react":
        stream_fn = react_agent.chat_stream             # NEW branch
    else:
        stream_fn = agent_chat_stream                   # existing

    async def event_generator():
        for chunk in stream_fn(req.message, req.session_id):
            # ... same SSE serialization as before ...

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## `POST /api/chat` (non-streaming) Handler Change

```python
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    mode = get_session_orchestration_mode(req.session_id or "")

    if mode == "react":
        response = react_agent.chat(req.message, req.session_id)
    else:
        response = agent_chat(req.message, req.session_id)

    return ChatResponse(**response.to_dict())
```

## Invariants

- `fashion_agent.py` is **never modified** — it is imported and called exactly as before
- `get_session_orchestration_mode()` returns `"direct"` for unknown sessions (safe fallback)
- The routing DB read (`get_session_orchestration_mode`) is one lightweight `SELECT` per message — acceptable overhead (~1ms)
- Both `fashion_agent` and `react_agent` return `AgentResponse` and yield the same `ThinkingEvent` / `SynthesisChunk` types — the SSE serialization layer is unchanged
