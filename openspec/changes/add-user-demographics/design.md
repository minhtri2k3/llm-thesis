## Context

The Fashion Agent (`fashion_agent` Python/FastAPI backend + `clothie_web` Flutter frontend) collects user session data for thesis evaluation. Currently, users register with only a name. The `user_sessions` PostgreSQL table and the `POST /api/sessions` endpoint need to accept two new demographic fields: year of birth and gender. The Flutter `RegisterScreen` must expose inputs for both fields before the user starts chatting.

Both services run under Docker Compose. The backend uses psycopg2 with a connection pool and incremental DDL migrations in `init_memory_tables()`.

## Goals / Non-Goals

**Goals:**
- Add `year_of_birth` (INT) and `gender` (TEXT enum `'male'`|`'female'`) to `user_sessions`.
- Collect these fields on the Flutter `RegisterScreen` before session creation.
- Pass them through `ApiService.createSession()` → `POST /api/sessions` → `create_session()`.
- Expose per-session demographics in `GET /api/ratings` so the Professor View can display them.
- Show a demographics panel (avg. rating by gender, avg. rating by age group) in the Professor View dialog.
- Rebuild Docker images after backend changes.

**Non-Goals:**
- Authentication or identity management.
- Editing demographics after session creation.
- GDPR/privacy controls (research context only).
- Token analytics changes.

## Decisions

### D1 — Extend `user_sessions` rather than a new table
**Decision**: Add `year_of_birth` and `gender` as nullable columns to the existing `user_sessions` table using `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.

**Rationale**: Consistent with the existing pattern (the `user_name` column was added the same way). Zero downtime — existing sessions get `NULL` for both columns, and analytics queries use `WHERE year_of_birth IS NOT NULL` to exclude incomplete data. A separate `user_profiles` table would add a join with no benefit at this scale.

**Alternatives considered**: New `user_profiles` table (discarded — over-engineered for a research prototype).

---

### D2 — Store gender as TEXT with a CHECK constraint
**Decision**: `gender TEXT CHECK (gender IN ('male', 'female'))`.

**Rationale**: Simple, readable in raw SQL. Avoids ENUM type (Postgres ENUMs require `ALTER TYPE` to extend). The UI shows "Boy" / "Girl" labels but the API and DB use `'male'` / `'female'`.

**Alternatives considered**: ENUM type (discarded — harder to evolve), BOOLEAN `is_female` (discarded — less readable).

---

### D3 — Birth year stored as INT, age computed at query time
**Decision**: Store `year_of_birth INT`. Age is derived as `EXTRACT(YEAR FROM created_at) - year_of_birth` in analytics queries.

**Rationale**: Immutable fact. Storing age would become stale. Age group bucketing (Under 20 / 20–29 / 30–39 / 40+) is done at query time with a CASE expression.

**Validation**: backend validates `1900 ≤ year_of_birth ≤ current_year`.

---

### D4 — Fields are optional at the API level, prompted-but-not-enforced on the UI
**Decision**: `CreateSessionRequest` marks both fields `Optional` with `None` default. The Flutter UI shows them as required (UI-side validation) to encourage completion, but the backend accepts `null` gracefully.

**Rationale**: Prevents blocking existing Gradio/direct API callers. If a user bypasses the Flutter UI, data degrades gracefully to `NULL`.

---

### D5 — Demographics surfaced through existing `GET /api/ratings` + a new `GET /api/demographics` endpoint
**Decision**: Add a lightweight `GET /api/demographics` endpoint (protected by `X-Admin-Key`) returning precomputed aggregate stats. `GET /api/ratings` entries also gain `year_of_birth` and `gender` fields.

**Rationale**: Keeps the Professor View fast (single aggregate query vs. client-side computation over potentially many entries). The Flutter `_ProfessorDashboardDialog` gets a second tab for demographics.

---

### D6 — Docker rebuild strategy
**Decision**: After backend changes, run `docker compose up --build -d` which rebuilds only changed images. No schema migration script needed — `init_memory_tables()` runs at startup and applies the `ALTER TABLE` idempotently.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Existing sessions have `NULL` demographics | Analytics always filter `WHERE year_of_birth IS NOT NULL` and `WHERE gender IS NOT NULL` |
| `ALTER TABLE` runs on every startup | `ADD COLUMN IF NOT EXISTS` is a no-op if column exists — safe and fast |
| `CHECK` constraint rejects invalid gender values already in DB | N/A — columns are new, no existing data |
| Flutter year-of-birth input UX (too many years in a picker) | Use a `TextField` with `keyboardType: TextInputType.number` and hint `YYYY (e.g. 2000)` |
| Professor View API call count increases | Add demographic endpoint alongside existing token analytics — one extra HTTP call |

## Migration Plan

1. Deploy backend container with updated `memory.py` — `init_memory_tables()` runs DDL migrations on startup.
2. Deploy frontend container — new `RegisterScreen` sends demographics on all new sessions.
3. Old sessions silently remain `NULL`; no data loss.

**Rollback**: Remove the two columns (`ALTER TABLE user_sessions DROP COLUMN year_of_birth, DROP COLUMN gender`) and revert backend/frontend containers. All existing data is preserved.

## Open Questions

- *(none — demographics scope is fully defined)*
