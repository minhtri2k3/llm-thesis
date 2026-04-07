## Context

The Fashion Agent (v2) uses a deterministic routing architecture where `_route_and_execute()` decides which tool to call based on classified intent. This was a deliberate choice (replacing an earlier ReAct loop) to improve speed, reliability, and cost. The system now stores user demographics (gender, birth year) in `user_sessions` but never uses them in prompts. Language detection uses regex which has known false-positive edge cases. The research platform tracks model usage across three LLMs (Gemini, GPT-4o, Claude) to compare quality — this change extends that comparison to include orchestration strategy.

## Goals / Non-Goals

**Goals:**
- Inject user gender into synthesis prompts with a 50/50 A/B control group for measurability
- Fix language detection regression (English queries → Spanish responses)
- Implement three distinct orchestration+synthesis modes keyed to model selection:
  - Mode A (Gemini): direct routing + Gemini synthesis (baseline)
  - Mode B (GPT-4o): Gemini agentic orchestrator + GPT-4o synthesis
  - Mode C (Claude): GPT-4o agentic orchestrator + Claude synthesis
- Capture orchestration metadata (mode, models, tool call sequence) in analytics
- Keep Mode A performance identical to current baseline

**Non-Goals:**
- Changing the frontend model selection flow (UI stays as-is)
- Adding new tools beyond the current set (search, clarify, selections)
- Per-user orchestration mode override (mode is determined entirely by model choice)
- Streaming orchestration (orchestrator always runs synchronously before synthesis)

## Decisions

### D1: Mode-to-model mapping is fixed

**Decision:** Orchestration mode is purely determined by `preferred_model`:
- `gemini-*` → Mode A (direct routing)
- `gpt-*` → Mode B (Gemini orchestrates → GPT synthesizes)
- `claude-*` → Mode C (GPT orchestrates → Claude synthesizes)

**Rationale:** This avoids UI changes, keeps the A/B split natural (users self-select model), and cleanly separates modes so each has a different orchestrator+synthesizer pairing. The thesis can then analyze model choice as a treatment variable.

**Alternative considered:** Random assignment of orchestration mode independent of model choice — rejected because it would confuse users seeing inconsistent behavior for the same model.

---

### D2: Agentic orchestrator uses native function/tool calling

**Decision:** For Modes B and C, use the native tool-calling API of the orchestrator model (Gemini `tools=` parameter, OpenAI `tools=` parameter) rather than a text-based ReAct prompt loop.

**Rationale:** Native tool calling is more reliable, structured, and easier to parse than free-text "Thought/Action/Observation" loops. Both Gemini and OpenAI SDKs support this natively. It also produces structured tool call records that are directly loggable to analytics.

**Alternative considered:** A custom ReAct prompt loop (which the codebase previously had) — rejected due to reliability issues that caused the v2 rewrite.

---

### D3: Orchestrator calls synthesis model; synthesis model does NOT have tool access

**Decision:** The orchestrator decides what to search/clarify, executes the tools, then passes results + conversation history to the synthesis model as a plain context (no tools). The synthesis model only generates the final natural-language response.

```
[Orchestrator] → calls tools → gets results
    ↓
Packages results into synthesis prompt
    ↓
[Synthesizer] → generates response text
```

**Rationale:** Clean separation of concerns. Synthesis model is expensive (GPT-4o, Claude) — keeping it tool-free reduces latency and token cost on the synthesis call. Also means synthesis quality is purely a function of language quality, not tool selection quality, which is what we want to measure.

---

### D4: Gender hint is 50/50 A/B at session creation time

**Decision:** When a session is created, a random coin flip determines `gender_hint_enabled` (TRUE/FALSE). This value is stored in `user_sessions` and used throughout the session.

**Rationale:** Randomization at session level (not turn level) gives more natural conversation flow — the model either always or never knows gender in a session. Analysis is then:
```sql
SELECT gender_hint_enabled, AVG(satisfaction_rating), gender_alignment_rate
FROM sessions GROUP BY gender_hint_enabled
```

**Alternative considered:** Gender hint always on — rejected because you can't measure counterfactual (would the model have gotten gender right without the hint?)

---

### D5: Language detection fix uses two defensive layers

**Decision:** 
1. Remove ambiguous Spanish words (`el`, `la`, `un`, `una`, `es`) from the regex — keep only unambiguous Spanish tokens (`quiero`, `necesito`, `busco`, `vestido`, `ropa`, `ñ`, `¿`, `¡` etc.)
2. Pass detected language as an explicit mandatory instruction to synthesis: `"YOU MUST respond exclusively in {language}."`

**Rationale:** Two layers means even if detection still fails (rare), the model instruction forces the correct language. Detection fix prevents the false positive; mandatory instruction is the safety net.

---

### D6: Orchestration mode logged per-turn in conversation_events

**Decision:** Add columns `orchestration_mode`, `orchestrator_model`, `synthesizer_model`, `tool_calls_json` to `conversation_events`. Populated on every turn.

**Rationale:** Enables per-turn analysis of latency, token cost, and quality split by mode. The `tool_calls_json` column captures what the orchestrator decided to call and in what order — key research data.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Agentic loop infinite or long tool call chains | Hard cap at 5 tool call iterations per turn; fallback to synthesis with partial results |
| Orchestrator chooses wrong tool or calls tool multiple times unnecessarily | Log all tool calls; mode comparison in analytics will surface this quantitatively |
| GPT-4o as orchestrator increases cost significantly for Claude sessions | Token costs are logged per turn — thesis can report actual cost differential |
| Gender A/B split may be unlucky (gender imbalance between groups) | Log gender + group for each session; re-randomize analysis can correct for this post-hoc |
| Language false positives still occur after regex fix | Second layer (explicit prompt instruction) catches these as a backup |
| Gemini function calling response format differs from OpenAI | Abstract into `orchestrate()` method with model-specific response parsing |

## Open Questions

- **Tool call timeout**: If `hybrid_search` takes >3s during an agentic loop, should we retry or return partial results? → Default: return partial, log timeout.
- **Fallback mode**: If the orchestrator model API is unavailable (e.g., GPT down), should Mode B/C fall back to Mode A? → Yes, with a warning logged. Graceful degradation is essential for research sessions.
- **Synthesis prompt for agentic modes**: The synthesis prompt currently assumes search results are pre-fetched by `_build_synthesis_context`. For agentic modes, search results come from the orchestrator's tool calls. The synthesis prompt template may need a variant that explicitly lists "tool results" rather than "search context."
