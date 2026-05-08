## Context

Fashion Agent runs `gemini-2.5-flash` exclusively today. The `multi-model-llm-tracking` proposal already designed (and partly built) the schema for multi-model token tracking — `user_sessions.preferred_model`, `llm_token_usage.{model_name, orchestration_mode, orchestrator_model, synthesizer_model, …}`, `mode_cost_summary` view — but the runtime path was reverted to direct routing on Gemini only, and `api/main.py:123` hard-rejects any `preferred_model` value other than `gemini-2.5-flash`.

The thesis advisor wants a controlled experiment proving that an agent's tool-call discipline matters as model prices climb. Earlier exploration narrowed the design from cross-provider (Claude/GPT/Gemini) to intra-Gemini, because cross-provider changes confound the price-vs-quality axis with prompt-format and tokenizer differences.

A live API check (2026-05-08) confirmed all four target models are reachable from the project's API key:

```
gemini-2.5-flash         1726 ms
gemini-2.5-pro           2972 ms
gemini-3.1-flash-lite    1023 ms
gemini-3.1-pro-preview   2758 ms
```

## Goals / Non-Goals

**Goals**:
- Compare 4 Gemini models in a single-blind controlled study (within-subject crossover, N=10–20)
- Capture tokens (in/out) and latency (intent, synthesis, total) per turn keyed by codename
- Expose an admin dashboard with the 4-cell summary AND the codename↔model mapping
- Preserve every pre-study row in `user_sessions`, `llm_token_usage`, ratings, behaviour funnels — and keep them queryable
- Ship behind a feature flag so toggling the flag off restores today's exact behaviour

**Non-Goals**:
- USD costing (deferred — only tokens for now)
- Cross-provider support (out of band)
- Resurrecting `agentic_orchestrator.py` (dormant stub stays dormant)
- Re-running caption generation with newer models (no preprocessing change)
- Letting end users pick their model (study uses server-side assignment; the historical "4 user-pickable buttons" idea is replaced by single-blind assignment)

## The 2×2 design

```
                        cheap tier               top tier
                        ─────────────────────    ─────────────────────
   Gen 2.5 (stable)     Indigo                   Crimson
                        gemini-2.5-flash         gemini-2.5-pro
                        (existing anchor)        (new, stable)

   Gen 3.1 (newest)     Emerald                  Amber
                        gemini-3.1-flash-lite    gemini-3.1-pro-preview
                        (new, stable)            (new, preview)
```

Three questions answerable from this layout:

1. **Effect of generation** — Indigo→Emerald and Crimson→Amber: does the newer cheap and top tier improve user behaviour?
2. **Effect of tier** — Indigo→Crimson and Emerald→Amber: is the Pro tier worth the latency/token cost?
3. **Interaction** — does the Pro premium shrink as the cheap tier matures? (Headline thesis claim if true.)

## Assignment: Latin square + Graeco-Latin task balancing

Each tester is in one of four groups; group assignment is round-robin on registration. Each group has its own session order:

```
   User group   Session 1     Session 2     Session 3     Session 4
   ──────────   ───────────   ───────────   ───────────   ───────────
   Group 1      T1·Indigo     T2·Crimson    T3·Emerald    T4·Amber
   Group 2      T2·Emerald    T3·Amber      T4·Indigo     T1·Crimson
   Group 3      T3·Crimson    T4·Indigo     T1·Amber      T2·Emerald
   Group 4      T4·Amber      T1·Emerald    T2·Crimson    T3·Indigo
```

Properties:
- Each model appears in each session position exactly once
- Each task appears in each session position exactly once
- Each (task, model) pair appears at most once across the 16 cells

`Tn` definitions (equivalent shopping prompts; final wording is a study-design artefact, not enforced by code):

```
   T1  Casual weekend outfit for a coffee date
   T2  Smart-casual look for an office in summer
   T3  Athleisure set for a weekend hike
   T4  Cosy loungewear for working from home
```

The `study_group` column on `user_sessions` records the user's group (`Group1`–`Group4`). The `agent_codename` column records the codename for each session. The actual model ID is in `preferred_model` (existing column).

## Codename mapping

Single source of truth, hardcoded in `agent/cohort.py` (new module):

```
   Indigo   → gemini-2.5-flash
   Crimson  → gemini-2.5-pro
   Emerald  → gemini-3.1-flash-lite
   Amber    → gemini-3.1-pro-preview
```

The mapping is FIXED for the duration of the study so all testers see consistent behaviour for each codename. The admin dashboard exposes the mapping; the tester UI does not.

## Data model

Schema changes are strictly additive. Pre-study rows keep their NULLs in the new columns and are filtered out of the cohort dashboard via `WHERE study_group IS NOT NULL`.

```
   user_sessions       (existing, additive)
   ─────────────────────────────────────────
   + study_group       TEXT  NULL       -- 'Group1' .. 'Group4'  | NULL = legacy
   + agent_codename    TEXT  NULL       -- 'Indigo' | 'Crimson' | 'Emerald' | 'Amber'
   ─ preferred_model   already exists; widened allowlist

   llm_token_usage     (existing, additive)
   ─────────────────────────────────────────
   + latency_ms             INT NOT NULL DEFAULT 0
   + intent_latency_ms      INT NOT NULL DEFAULT 0
   + synthesis_latency_ms   INT NOT NULL DEFAULT 0
```

## Latency instrumentation

Three timers in `agent/fashion_agent.py`. The total wraps the whole stream; the inner two wrap the LLM-bearing steps so the dashboard can decompose total = (intent + search + synthesis + housekeeping).

```
   _orchestrate_stream()
   ─────────────────────
   t_total_start
   ├─ t_intent_start
   │     classify_intent(...)
   │  t_intent_end                    → intent_latency_ms
   │
   ├─ slot gate, search engine        (no LLM here, but search_ms is
   │                                   logged in the existing duration_ms
   │                                   on the SSE event for sanity)
   │
   ├─ t_synth_start
   │     _synthesize_response_stream(...)
   │  t_synth_end                     → synthesis_latency_ms
   │
   └─ t_total_end                     → latency_ms
```

`log_token_usage()` gains three optional kwargs (`latency_ms`, `intent_latency_ms`, `synthesizer_latency_ms`); old callers stay valid because all three default to 0.

## Feature-flag rollout

```
   ENABLE_COHORT_STUDY=false   (default)
     ─ validator behaves exactly as today (rejects non-2.5-flash)
     ─ create_session ignores study fields
     ─ /api/analytics/cohort returns 503 with "study not enabled"
     ─ smoke test skipped
     ─ FE registration shows existing fields only

   ENABLE_COHORT_STUDY=true
     ─ validator allows 4 cohort model IDs
     ─ create_session assigns Group1..4 round-robin → derives session 1
       order via Latin square → returns codename + model
     ─ each subsequent /api/sessions for the same user_name advances to
       the next session in their group's order, until all 4 are done
     ─ /api/analytics/cohort returns the 4-cell table
     ─ smoke test runs at boot; cells with unreachable models are
       removed from rotation and surface a startup warning
     ─ FE registration hides model picker; shows codename of assigned model
```

The flag flip is the entire rollout / rollback control. Toggling false → true changes API behaviour; flipping true → false reverts new sessions to today's behaviour. Existing data is unaffected either way.

## Smoke test

Added to FastAPI startup (`api/main.py` lifespan handler). When `ENABLE_COHORT_STUDY=true`:

```
   for each model_id in {indigo,crimson,emerald,amber}:
       try: GeminiClient(model_id).generate("ping")  # 1-token cost
       except: log.error(...); _UNREACHABLE_CODES.add(codename)
```

If any cell is unreachable, log a loud warning, and `assign_cohort_session()` skips that codename. If 0 cells are reachable, the API refuses to enable cohort mode (returns 500 on `/api/sessions` with a clear error). This prevents a silent degradation where Group 4 testers all hit a dead Amber cell.

## Cohort dashboard endpoint

`GET /api/analytics/cohort` returns:

```json
{
  "mapping": {
    "Indigo":  "gemini-2.5-flash",
    "Crimson": "gemini-2.5-pro",
    "Emerald": "gemini-3.1-flash-lite",
    "Amber":   "gemini-3.1-pro-preview"
  },
  "cells": [
    {
      "codename": "Indigo",
      "model": "gemini-2.5-flash",
      "n_sessions": 5, "n_turns": 23,
      "tokens": { "input_per_turn": 1240, "output_per_turn": 380, "total_per_session": 7400 },
      "latency_ms": { "total_p50": 1900, "total_p95": 4100, "intent_p50": 320, "synthesis_p50": 1480 },
      "behaviour": { "click_through_rate": 0.62, "cart_adds_per_session": 1.4, "avg_rating": 4.2,
                     "clarification_rate": 0.18, "turns_to_first_cart": 2.1 }
    },
    { ... three more ... }
  ]
}
```

Implementation: a single SQL query joining `llm_token_usage` × `user_sessions` × `user_ratings` × `session_path_funnel_summary` filtered to `study_group IS NOT NULL`, grouped by `agent_codename`. Mapping is read from the codename module.

The dashboard renders this as a 4-column table in `professor_dashboard_page.dart`, with the mapping shown in a header strip ("Indigo = Gemini 2.5 Flash …"). Admin-only view; testers never see it.

## Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| `gemini-3.1-pro-preview` behaviour shifts mid-study (Preview status) | Med | Lock test window ≤ 2 weeks; record snapshot date per session |
| Test in `tests/test_orchestration_modes.py` breaks if `_get_orchestration_mode` is changed | Med | Keep return shape `("direct", "gemini-2.5-flash", model_id)`; do not change orchestrator label |
| Latency added to a streaming path could miscount streaming time | Low | Wrap `_synthesize_response_stream()` start→exhaustion of generator; document that synthesis_ms includes streaming wait |
| User registers 4 times with same name → 5th session leaks back to Group's session 1 | Low | API rejects 5th `/api/sessions` for the same user_name when cohort mode is on with HTTP 409 |
| Pre-study legacy rows polluting cohort dashboard | Low | All cohort queries filter `study_group IS NOT NULL` |
| Group counts uneven if N % 4 ≠ 0 | Low | Acceptable; record actual group sizes in the dashboard so the analyst sees imbalance |

## What we are NOT doing (and why)

- **Not using LLMClient abstraction-level cleanup**. The four direct-Gemini callsites (`intent_classifier`, `clarification_gate`, `query_expansion`, plus synthesis) all use `get_model()` today. Since all four cohort models are Gemini, the existing `get_model(model_id)` works without refactor. Touching them adds risk for zero behavioural gain in this study.
- **Not adding USD pricing**. The thesis question is "does the user behaviour improve?", and tokens-per-turn is the cost axis. USD adds noise (preview pricing isn't published; `mode_cost_summary` constants are stale). Defer until a follow-up.
- **Not implementing user-pickable buttons during the study**. Earlier discussion considered showing 4 buttons; rejected because user-choice contaminates the cohort with self-selection bias. Server assignment is the only correct design for a controlled study.
