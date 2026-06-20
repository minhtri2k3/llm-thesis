## Why

The `fashion_agent/agent` package contains a mix of English docstrings and a number of undocumented helpers. That makes the pipeline harder to navigate and makes it difficult to reference methods directly when reading the source.

## What Changes

- Add Vietnamese module docstrings to every Python file in `fashion_agent/agent`, including `__init__.py`.
- Add Vietnamese docstrings for public classes, public functions, dataclasses, and important private helpers.
- Describe purpose, inputs, outputs, and the role each method plays in the agent pipeline.
- Keep behavior unchanged; this is documentation-only work.

## Capabilities

### New Capabilities
- `vietnamese-agent-docstrings`: Vietnamese in-code documentation for the agent package.

## Impact

- `fashion_agent/agent/__init__.py`
- `fashion_agent/agent/clarification_gate.py`
- `fashion_agent/agent/intent_classifier.py`
- `fashion_agent/agent/slot_completeness.py`
- `fashion_agent/agent/prompts.py`
- `fashion_agent/agent/tools.py`
- `fashion_agent/agent/utils.py`
- `fashion_agent/agent/agentic_orchestrator.py`
- `fashion_agent/agent/fashion_agent.py`
- `fashion_agent/agent/react_agent.py`
- `fashion_agent/agent/memory.py`

No API, schema, retrieval, or orchestration behavior changes are expected.
