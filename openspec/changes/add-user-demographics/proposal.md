## Why

The Fashion Agent thesis study needs demographic breakdowns to validate whether the RAG-based fashion recommendation system performs consistently across different age groups and genders, turning raw session ratings into statistically useful research data. Without year of birth and gender, the evaluation dataset cannot support claims about cross-demographic usability.

## What Changes

- **RegisterScreen (Flutter)** gains two new required fields: a birth year number input and a binary gender selector (Boy / Girl toggle).
- **`POST /api/sessions`** (`CreateSessionRequest`) gains two optional fields: `year_of_birth: Optional[int]` and `gender: Optional[str]` (`"male"` | `"female"`).
- **`create_session()`** in `agent/memory.py` accepts and persists the two new fields.
- **`init_memory_tables()`** adds two new columns to `user_sessions` via `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (no-downtime migration).
- **`GET /api/ratings`** includes `year_of_birth` and `gender` in each entry so the Professor View can show demographics.
- **Professor View** (Flutter modal) gets a demographics summary panel showing average rating by gender and by age group.
- **Docker** rebuild is required after backend changes (`docker compose up --build`).

## Capabilities

### New Capabilities

- `user-demographics`: Capture year of birth and gender at session creation time and persist them alongside session data for research analysis.
- `demographics-analytics`: Expose demographic breakdowns (avg. rating by gender, avg. rating by age group) through the existing ratings/analytics API surface and display them in the Professor View.

### Modified Capabilities

- *(none — no existing spec-level behavior changes)*

## Impact

- **Backend** — `fashion_agent/agent/memory.py`, `fashion_agent/api/main.py`
- **Database** — `user_sessions` table gains `year_of_birth INT` and `gender TEXT` columns (additive migration, no breaking change)
- **Frontend** — `clothie_web/lib/screens/register_screen.dart`, `clothie_web/lib/services/api_service.dart`
- **Docker** — rebuild backend image; no new services required
- **Existing data** — all previous sessions will have `NULL` for the new columns; analytics queries filter `WHERE year_of_birth IS NOT NULL`
