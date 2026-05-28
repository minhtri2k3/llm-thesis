# Spec: db-schema

## Overview

All schema changes are applied via idempotent DDL inside `init_memory_tables()` in `agent/memory.py`. No migration tool is needed. Applied automatically on `docker compose restart fashion-api`.

## New Column: `user_sessions.orchestration_mode`

```sql
ALTER TABLE user_sessions
    ADD COLUMN IF NOT EXISTS orchestration_mode TEXT NOT NULL DEFAULT 'direct'
    CHECK (orchestration_mode IN ('direct', 'react'));
```

**Effect on existing rows:** PostgreSQL backfills all existing sessions with `'direct'` atomically. No data loss. Lock duration: milliseconds for the expected row count.

## New Columns: `llm_token_usage`

```sql
ALTER TABLE llm_token_usage
    ADD COLUMN IF NOT EXISTS response_latency_ms FLOAT NOT NULL DEFAULT 0;

ALTER TABLE llm_token_usage
    ADD COLUMN IF NOT EXISTS llm_call_count INT NOT NULL DEFAULT 1;
```

## New Table: `react_traces`

```sql
CREATE TABLE IF NOT EXISTS react_traces (
    id            BIGSERIAL PRIMARY KEY,
    session_id    TEXT    NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
    query_text    TEXT    NOT NULL,
    iteration     INT     NOT NULL DEFAULT 0,
    tool_name     TEXT    NOT NULL DEFAULT '',
    tool_args     JSONB   NOT NULL DEFAULT '{}',
    result_count  INT     NOT NULL DEFAULT 0,
    duration_ms   FLOAT   NOT NULL DEFAULT 0,
    traced_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_react_traces_session
    ON react_traces(session_id, traced_at);
```

**Note:** Only rows from ReAct sessions will be inserted. Direct sessions will have zero rows in this table — this is the expected invariant and can be verified in smoke tests.

## New Table: `eval_queries`

```sql
CREATE TABLE IF NOT EXISTS eval_queries (
    id            SERIAL PRIMARY KEY,
    query_text    TEXT    NOT NULL UNIQUE,
    relevant_ids  JSONB   NOT NULL DEFAULT '[]',
    category      TEXT    NOT NULL DEFAULT '',
    difficulty    TEXT    NOT NULL DEFAULT 'medium'
                  CHECK (difficulty IN ('easy', 'medium', 'hard')),
    language      TEXT    NOT NULL DEFAULT 'en'
                  CHECK (language IN ('en', 'vi')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## New Table: `eval_results`

```sql
CREATE TABLE IF NOT EXISTS eval_results (
    id                  BIGSERIAL PRIMARY KEY,
    eval_query_id       INT     NOT NULL REFERENCES eval_queries(id),
    orchestration_mode  TEXT    NOT NULL CHECK (orchestration_mode IN ('direct', 'react')),
    returned_ids        JSONB   NOT NULL DEFAULT '[]',
    hit_at_1            BOOLEAN NOT NULL DEFAULT FALSE,
    hit_at_3            BOOLEAN NOT NULL DEFAULT FALSE,
    hit_at_6            BOOLEAN NOT NULL DEFAULT FALSE,
    reciprocal_rank     FLOAT   NOT NULL DEFAULT 0,
    ndcg_at_6           FLOAT   NOT NULL DEFAULT 0,
    latency_ms          FLOAT   NOT NULL DEFAULT 0,
    llm_call_count      INT     NOT NULL DEFAULT 0,
    total_tokens        INT     NOT NULL DEFAULT 0,
    run_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_query_mode
    ON eval_results(eval_query_id, orchestration_mode);
```

## New Helper: `get_session_orchestration_mode()`

```python
def get_session_orchestration_mode(session_id: str) -> str:
    """Return 'direct' | 'react' for the given session. Defaults to 'direct' on not-found."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT orchestration_mode FROM user_sessions WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
    return row[0] if row else "direct"
```

## Deployment Checklist

```bash
# On Mac Mini (SSH or direct):
cd ~/path/to/fashion_agent
docker compose restart fashion-api

# Verify:
docker compose logs fashion-api --tail=30
# Expected: "Memory tables initialized."

# Confirm new columns exist:
docker compose exec postgres psql -U fashion_user -d fashion_rag \
  -c "\d user_sessions" | grep orchestration_mode
# Expected: orchestration_mode | text | not null | 'direct'::text
```
