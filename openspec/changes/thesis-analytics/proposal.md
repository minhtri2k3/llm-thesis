## Why

The thesis research requires quantitative evidence of LLM resource consumption per conversation session. Currently token usage is computed in memory and discarded; there is no persistent record of how many tokens Gemini spends per intent classification or response synthesis call, nor any record of which ranked position the user selected (1-6) from reranker results. A password-protected professor dashboard is needed to present these analytics without exposing raw data to regular users.

## What Changes

- New `llm_token_usage` PostgreSQL table to persist per-call token counts (input, output, model name, call type)
- New `session_token_summary` view for aggregate token reporting per session
- Hooks in `fashion_agent.py` to call `log_token_usage()` after intent classification and synthesis streaming
- New `ADMIN_SECRET_KEY` environment variable (value: `21042024`) controlling dashboard access
- New `GET /api/analytics/token-usage` FastAPI endpoint protected by the secret key
- New Flutter `_ProfessorDashboardDialog` widget on the Register screen — accessible via a "🔬 Professor View" button, gated by an 8-digit PIN dialog
- New `getTokenAnalytics(secretKey)` method in `ApiService`

## Capabilities

### New Capabilities

- `llm-token-tracking`: Per-call LLM token usage logged to PostgreSQL; aggregated by session with model name, input tokens, output tokens, and total tokens.
- `professor-dashboard`: Password-protected analytics dashboard in the Flutter Register screen showing Model Name, Total Tokens, Session ID, and User Name per session.

### Modified Capabilities

<!-- No existing spec-level requirements change. -->

## Impact

- **Backend**: `agent/memory.py` (new table + view + `log_token_usage()` function), `agent/fashion_agent.py` (2 new callsites for token logging), `api/main.py` (1 new endpoint)
- **Environment**: `.env` and `.env.example` gain `ADMIN_SECRET_KEY=21042024`
- **Flutter**: `services/api_service.dart` (1 new method), `screens/register_screen.dart` (new button + 2 new dialog widgets)
- **Dependencies**: No new Python packages required; no new Flutter packages required
- **Database**: Additive-only DDL (new table + view); no existing tables altered
