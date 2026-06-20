## Context

The agent package has several layers: intent extraction, clarification, deterministic routing, synthesis, agentic orchestration, and PostgreSQL-backed session memory. Some files already have English docstrings, while others have no docstrings on helper methods. The requested change is to make the source easier to read by providing Vietnamese documentation directly in code.

## Goals / Non-Goals

**Goals:**
- Add Vietnamese module docstrings to every file in `fashion_agent/agent`.
- Add Vietnamese docstrings to each class, function, and important helper in the package.
- Keep the wording short but specific enough to act as a reference for nearby methods.
- Preserve runtime behavior exactly.

**Non-Goals:**
- Do not change prompt template text used by the LLM.
- Do not change search, memory, or orchestration logic.
- Do not add new features, tests, or schema migrations as part of this change.

## Decisions

1. Use Vietnamese for all new docstrings and translate existing English docstrings where they are part of the documented API.
2. Keep identifier names in English so the docs remain aligned with the code.
3. Add module docstrings first, then function/class docstrings, so each file can stand alone as a reference.
4. Include private helpers when they are part of the pipeline or carry non-obvious behavior.

## Risks / Trade-offs

- Large patch surface across many files may introduce formatting mistakes.
- Some files contain many helper methods, so the docstrings need to stay concise to avoid becoming noise.
- Prompt constants remain English by design; only docstrings and explanatory comments should be localized.
