## Why

The thesis investigates the question: **as LLM token costs rise across model generations and tiers, does the agent system's behaviour-driven output quality justify the price premium?** To answer it, we need a controlled cohort study comparing 4 Gemini models on real user behaviour, while preserving the single-model production system and its existing data.

The currently shipped agent runs only `gemini-2.5-flash`. The dormant `multi-model-llm-tracking` proposal scoped a cross-provider (Gemini/GPT/Claude) abstraction; that scope is out of band — Claude/GPT introduce SDK, prompt-format, and tokenizer confounds that obscure the price-vs-quality signal. This change constrains the study to a clean intra-Gemini 2×2 factorial design (generation × tier) so the only variable that moves is *model capability*.

## What Changes

- **4-model lineup** behind a feature flag (`ENABLE_COHORT_STUDY`). The existing `gemini-2.5-flash` remains the default; three additional IDs become valid: `gemini-2.5-pro`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`.
- **Codename blinding**: testers see neutral codenames (`Indigo`, `Crimson`, `Emerald`, `Amber`); the admin dashboard reveals the mapping. Mapping is fixed across the study.
- **Within-subject crossover**: each tester completes 4 sessions, one per model, ordered by a Latin square. Server assigns the model — the user does not choose.
- **Graeco-Latin task balancing**: 4 equivalent shopping tasks (`T1`-`T4`) crossed with 4 models so each task and each model appears once in each position across user groups.
- **Latency instrumentation**: wall-clock per LLM call (intent + synthesis) and total per-turn latency captured into `llm_token_usage`. No USD pricing computed for now — only token counts and timings.
- **Startup smoke test**: when `ENABLE_COHORT_STUDY=true`, the API verifies access to all 4 model IDs at boot; failure surfaces a loud warning and excludes the unreachable cell from rotation.
- **Cohort dashboard**: new admin endpoint `GET /api/analytics/cohort` returns the 4-cell table (tokens, latency, behaviour funnel, ratings) keyed by codename, with the codename↔model mapping explicit in the response.
- **Single-blind preservation of existing data**: schema changes are additive only (`ADD COLUMN IF NOT EXISTS …`). All pre-study sessions remain queryable; cohort sessions are tagged `study_group IS NOT NULL` so analyses can filter cleanly.

## Capabilities

### New Capabilities

- `cohort-evaluation`: 4-Gemini cohort study with Latin-square assignment, Graeco-Latin task balancing, codename blinding, latency instrumentation, and admin dashboard

### Modified Capabilities

- `multi-model-llm` (from `multi-model-llm-tracking`): widen `preferred_model` allowlist from `{gemini-2.5-flash}` to the 4 IDs above; dispatch stays Gemini-only via `GeminiClient`
- `model-selection`: validator accepts cohort study models; under `ENABLE_COHORT_STUDY=true`, the API overrides client-supplied `preferred_model` with the server-assigned model

## Impact

**Code files (additive — none deleted)**:
- `fashion_agent/api/main.py` — widen `CreateSessionRequest` validator; add `_is_cohort_study_enabled()` helper; add `GET /api/analytics/cohort`; add startup smoke-test hook
- `fashion_agent/agent/memory.py` — `ALTER TABLE … ADD COLUMN IF NOT EXISTS` for `latency_ms`, `intent_latency_ms`, `synthesis_latency_ms` on `llm_token_usage`; for `study_group`, `agent_codename` on `user_sessions`; new `assign_cohort_session()` and `get_cohort_summary()` helpers
- `fashion_agent/agent/fashion_agent.py` — wrap `classify_intent()` and synthesis calls with `time.perf_counter()`; pass latencies into `log_token_usage()` (signature widened with optional kwargs)
- `fashion_agent/api/analytics.py` — new `cohort_summary()` query joining `llm_token_usage` × `user_sessions` × ratings, grouped by `agent_codename`
- `fashion_agent/shared/llm.py` — no functional change; `get_client(name)` already caches per name
- `clothie_web/lib/screens/register_screen.dart` — when in cohort mode, hide model picker and display assigned codename only; otherwise behaviour unchanged
- `clothie_web/lib/screens/professor_dashboard_page.dart` — new "Cohort Study" tab consuming `/api/analytics/cohort`; admin-only view shows codename↔model mapping

**Configuration**:
- `docker-compose.yml` — add `ENABLE_COHORT_STUDY: ${ENABLE_COHORT_STUDY:-false}`
- `.env` example — document `ENABLE_COHORT_STUDY` (default `false`)

**Database (additive only — preserves all existing rows)**:
- `user_sessions` gains `study_group TEXT`, `agent_codename TEXT` (nullable; legacy rows stay NULL)
- `llm_token_usage` gains `latency_ms INT`, `intent_latency_ms INT`, `synthesizer_latency_ms INT` (default 0)

**Out of scope (explicitly NOT changed)**:
- `pre_processing/processing_data.py` — caption generation stays on `gemini-2.5-flash`; no re-ingest
- `agent/agentic_orchestrator.py` — dormant stub remains untouched
- `mode_cost_summary` USD pricing — stale 2.0-Flash constants left as-is; no USD computed for this study
- Cross-provider (`OpenAIClient`, `AnthropicClient`) abstractions — remain absent
- The 8 assertions in `tests/test_orchestration_modes.py` — `_get_orchestration_mode()` keeps returning `("direct", "gemini-2.5-flash", model_id)` so all 8 pass unchanged

**No breaking changes** — feature flag default OFF restores byte-identical behaviour to today.
