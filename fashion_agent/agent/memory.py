"""Session memory backed by PostgreSQL."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""


@dataclass
class Session:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: str = ""


# ---------------------------------------------------------------------------
# Connection pool (singleton)
# ---------------------------------------------------------------------------

_pool = None  # type: SimpleConnectionPool | None  (lazy import)


def _get_pool():
    """Return (and lazily create) the module-level connection pool."""
    from psycopg2.pool import SimpleConnectionPool

    global _pool
    if _pool is None or _pool.closed:
        _pool = SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
            options="-c lock_timeout=8000",  # 8s lock timeout — prevents indefinite hang
        )
    return _pool


@contextmanager
def _db_conn():
    """Context manager that borrows a connection and always returns it."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def init_memory_tables() -> None:
    """Create session tables if they don't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS conversation_history (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_conv_history_session
        ON conversation_history(session_id, created_at);

    -- Memory Agent: JSONB columns for preference tracking
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS liked_items JSONB NOT NULL DEFAULT '[]'::jsonb;
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS query_history JSONB NOT NULL DEFAULT '[]'::jsonb;

    -- Product selection: stores user-confirmed product selections
    CREATE TABLE IF NOT EXISTS selected_items (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id VARCHAR NOT NULL,
        label VARCHAR NOT NULL DEFAULT '',
        color VARCHAR NOT NULL DEFAULT '',
        caption TEXT NOT NULL DEFAULT '',
        image_path VARCHAR NOT NULL DEFAULT '',
        search_query TEXT NOT NULL DEFAULT '',
        path_mode TEXT NOT NULL DEFAULT 'path1' CHECK (path_mode IN ('path1', 'path2')),
        selected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, image_id, path_mode)
    );

    CREATE INDEX IF NOT EXISTS idx_selected_items_session
        ON selected_items(session_id, selected_at);

    -- Model tracking: user intent over single model
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS preferred_model TEXT DEFAULT 'gemini-2.5-flash';

    -- Clothie Web FE: user name tracking per session
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS user_name TEXT NOT NULL DEFAULT '';

    -- Thesis research: demographic fields for cross-age/gender analysis
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS year_of_birth INT;
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS gender TEXT CHECK (gender IN ('male', 'female'));

    -- Clothie Web FE: thesis evaluation ratings
    CREATE TABLE IF NOT EXISTS user_ratings (
        id          SERIAL PRIMARY KEY,
        session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        user_name   TEXT NOT NULL DEFAULT '',
        rating      INT  NOT NULL CHECK (rating BETWEEN 1 AND 10),
        feedback    TEXT NOT NULL DEFAULT '',
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_user_ratings_session
        ON user_ratings(session_id);

    -- Thesis evaluation v2: 1-5 scale, three targeted questions
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_overall INT
            CHECK (rating_overall BETWEEN 1 AND 5);
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_suggestions INT
            CHECK (rating_suggestions BETWEEN 1 AND 5);
    ALTER TABLE user_ratings
        ADD COLUMN IF NOT EXISTS rating_conversation INT
            CHECK (rating_conversation BETWEEN 1 AND 5);

    -- LLM Token Usage: per-call token tracking for thesis reporting
    CREATE TABLE IF NOT EXISTS llm_token_usage (
        id          BIGSERIAL PRIMARY KEY,
        session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        call_name   TEXT NOT NULL,
        model_name  TEXT NOT NULL,
        input_tokens  INT NOT NULL DEFAULT 0,
        output_tokens INT NOT NULL DEFAULT 0,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_llm_token_usage_session
        ON llm_token_usage(session_id, created_at);

    -- Behaviour: tracking selection position in ranked list
    ALTER TABLE selected_items
        ADD COLUMN IF NOT EXISTS position INT NOT NULL DEFAULT 0;

    -- Behaviour: cart removal logic
    CREATE TABLE IF NOT EXISTS cart_removals (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id VARCHAR NOT NULL,
        removed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_cart_removals_session
        ON cart_removals(session_id);

    -- ── Behaviour: products shown per search result ────────────────────
    CREATE TABLE IF NOT EXISTS product_impressions (
        id           BIGSERIAL PRIMARY KEY,
        session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id     VARCHAR NOT NULL,
        search_query TEXT NOT NULL DEFAULT '',
        path_mode    TEXT NOT NULL DEFAULT 'path1' CHECK (path_mode IN ('path1', 'path2')),
        position     INT NOT NULL DEFAULT 0,
        shown_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_impressions_session
        ON product_impressions(session_id, shown_at);

    -- ── Behaviour: product card taps (click events) ────────────────────
    CREATE TABLE IF NOT EXISTS product_clicks (
        id           BIGSERIAL PRIMARY KEY,
        session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id     VARCHAR NOT NULL,
        position     INT NOT NULL DEFAULT 0,
        search_query TEXT NOT NULL DEFAULT '',
        path_mode    TEXT NOT NULL DEFAULT 'path1' CHECK (path_mode IN ('path1', 'path2')),
        clicked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_clicks_session
        ON product_clicks(session_id, clicked_at);

    -- ── Behaviour: purchase intent signals ────────────────────────────
    CREATE TABLE IF NOT EXISTS product_intents (
        id            BIGSERIAL PRIMARY KEY,
        session_id    TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        image_id      VARCHAR NOT NULL,
        intent_type   TEXT NOT NULL CHECK (intent_type IN ('will_buy', 'not_for_me')),
        reason        TEXT NOT NULL DEFAULT '',
        path_mode     TEXT NOT NULL DEFAULT 'path1' CHECK (path_mode IN ('path1', 'path2')),
        logged_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, image_id, intent_type, path_mode)
    );

    CREATE INDEX IF NOT EXISTS idx_intents_session
        ON product_intents(session_id, logged_at);

    -- ── Checkout: simulated order (phone + address) ───────────────────
    CREATE TABLE IF NOT EXISTS user_orders (
        id          SERIAL PRIMARY KEY,
        session_id  TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        phone       TEXT NOT NULL DEFAULT '',
        address     TEXT NOT NULL DEFAULT '',
        path_mode   TEXT NOT NULL DEFAULT 'path1' CHECK (path_mode IN ('path1', 'path2')),
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_orders_session
        ON user_orders(session_id);

    -- ── Session lifecycle: when and how session ended ─────────────────
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS ended_by TEXT
            CHECK (ended_by IN ('order', 'rating', 'timeout'));

    -- ── Multi-model A/B: gender hint control group ────────────────────
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS gender_hint_enabled BOOLEAN NOT NULL DEFAULT FALSE;

    -- ── Multi-model A/B: orchestration analytics per conversation turn ─
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS orchestration_mode TEXT;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS orchestrator_model TEXT;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS synthesizer_model TEXT;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS tool_calls_json JSONB NOT NULL DEFAULT '[]'::jsonb;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS orchestrator_input_tokens INT NOT NULL DEFAULT 0;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS orchestrator_output_tokens INT NOT NULL DEFAULT 0;

    -- Ensure path_mode exists on existing databases
    ALTER TABLE product_impressions
        ADD COLUMN IF NOT EXISTS path_mode TEXT NOT NULL DEFAULT 'path1';
    ALTER TABLE product_clicks
        ADD COLUMN IF NOT EXISTS path_mode TEXT NOT NULL DEFAULT 'path1';
    ALTER TABLE product_intents
        ADD COLUMN IF NOT EXISTS path_mode TEXT NOT NULL DEFAULT 'path1';
    ALTER TABLE user_orders
        ADD COLUMN IF NOT EXISTS path_mode TEXT NOT NULL DEFAULT 'path1';
    ALTER TABLE selected_items
        ADD COLUMN IF NOT EXISTS path_mode TEXT NOT NULL DEFAULT 'path1';

    -- Widen uniqueness to include path_mode
    DO $$
    BEGIN
        BEGIN
            ALTER TABLE selected_items DROP CONSTRAINT selected_items_session_id_image_id_key;
        EXCEPTION WHEN undefined_object THEN
            NULL;
        END;
    END $$;
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'selected_items_session_id_image_id_path_mode_key'
        ) THEN
            ALTER TABLE selected_items
                ADD CONSTRAINT selected_items_session_id_image_id_path_mode_key
                UNIQUE (session_id, image_id, path_mode);
        END IF;
    END $$;

    DO $$
    BEGIN
        BEGIN
            ALTER TABLE product_intents DROP CONSTRAINT product_intents_session_id_image_id_intent_type_key;
        EXCEPTION WHEN undefined_object THEN
            NULL;
        END;
    END $$;
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'product_intents_session_id_image_id_intent_type_path_mode_key'
        ) THEN
            ALTER TABLE product_intents
                ADD CONSTRAINT product_intents_session_id_image_id_intent_type_path_mode_key
                UNIQUE (session_id, image_id, intent_type, path_mode);
        END IF;
    END $$;

    -- ── ReAct pipeline comparison: session pipeline tag ───────────────
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS orchestration_mode TEXT NOT NULL DEFAULT 'direct'
        CHECK (orchestration_mode IN ('direct', 'react'));

    -- ── ReAct pipeline comparison: per-call efficiency metrics ────────
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS response_latency_ms FLOAT NOT NULL DEFAULT 0;
    ALTER TABLE llm_token_usage
        ADD COLUMN IF NOT EXISTS llm_call_count INT NOT NULL DEFAULT 1;

    -- ── ReAct pipeline comparison: per-iteration tool-call traces ─────
    CREATE TABLE IF NOT EXISTS react_traces (
        id           BIGSERIAL PRIMARY KEY,
        session_id   TEXT NOT NULL REFERENCES user_sessions(session_id) ON DELETE CASCADE,
        query_text   TEXT NOT NULL DEFAULT '',
        iteration    INT NOT NULL DEFAULT 0,
        tool_name    TEXT NOT NULL DEFAULT '',
        tool_args    JSONB NOT NULL DEFAULT '{}'::jsonb,
        result_count INT NOT NULL DEFAULT 0,
        duration_ms  FLOAT NOT NULL DEFAULT 0,
        traced_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_react_traces_session
        ON react_traces(session_id, traced_at);

    -- ── Offline evaluation: ground truth query set ────────────────────
    CREATE TABLE IF NOT EXISTS eval_queries (
        id           SERIAL PRIMARY KEY,
        query_text   TEXT NOT NULL UNIQUE,
        relevant_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
        category     TEXT NOT NULL DEFAULT '',
        difficulty   TEXT NOT NULL DEFAULT 'medium'
            CHECK (difficulty IN ('easy', 'medium', 'hard')),
        language     TEXT NOT NULL DEFAULT 'en'
            CHECK (language IN ('en', 'vi')),
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- ── Offline evaluation: per-query per-mode results ────────────────
    CREATE TABLE IF NOT EXISTS eval_results (
        id                BIGSERIAL PRIMARY KEY,
        eval_query_id     INT NOT NULL REFERENCES eval_queries(id) ON DELETE CASCADE,
        orchestration_mode TEXT NOT NULL DEFAULT 'direct',
        returned_ids      JSONB NOT NULL DEFAULT '[]'::jsonb,
        hit_at_1          BOOL NOT NULL DEFAULT FALSE,
        hit_at_3          BOOL NOT NULL DEFAULT FALSE,
        hit_at_6          BOOL NOT NULL DEFAULT FALSE,
        reciprocal_rank   FLOAT NOT NULL DEFAULT 0,
        ndcg_at_6         FLOAT NOT NULL DEFAULT 0,
        latency_ms        FLOAT NOT NULL DEFAULT 0,
        llm_call_count    INT NOT NULL DEFAULT 0,
        total_tokens      INT NOT NULL DEFAULT 0,
        run_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_eval_results_query_mode
        ON eval_results(eval_query_id, orchestration_mode);

    -- ── RAG Ablation Study: per-retrieval-mode offline results ───────────
    -- Stores results for each retrieval variant (bm25_only, siglip_only, etc.)
    -- independent from the pipeline orchestration comparison (eval_results).
    CREATE TABLE IF NOT EXISTS rag_ablation_results (
        id              BIGSERIAL PRIMARY KEY,
        eval_query_id   INT NOT NULL REFERENCES eval_queries(id) ON DELETE CASCADE,
        retrieval_mode  TEXT NOT NULL,
        returned_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,
        hit_at_1        BOOL NOT NULL DEFAULT FALSE,
        hit_at_3        BOOL NOT NULL DEFAULT FALSE,
        hit_at_6        BOOL NOT NULL DEFAULT FALSE,
        reciprocal_rank FLOAT NOT NULL DEFAULT 0,
        ndcg_at_6       FLOAT NOT NULL DEFAULT 0,
        latency_ms      FLOAT NOT NULL DEFAULT 0,
        run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_rag_ablation_query_mode
        ON rag_ablation_results(eval_query_id, retrieval_mode);
    """

    view_ddl = """
    CREATE OR REPLACE VIEW session_token_summary AS
    SELECT
        s.session_id,
        s.user_name,
        MAX(u.model_name)              AS model_name,
        SUM(u.input_tokens)            AS total_input_tokens,
        SUM(u.output_tokens)           AS total_output_tokens,
        SUM(u.input_tokens + u.output_tokens) AS total_tokens,
        SUM(u.orchestrator_input_tokens)  AS total_orchestrator_input_tokens,
        SUM(u.orchestrator_output_tokens) AS total_orchestrator_output_tokens,
        MAX(u.orchestration_mode)      AS orchestration_mode,
        MAX(u.orchestrator_model)      AS orchestrator_model,
        MAX(u.synthesizer_model)       AS synthesizer_model,
        s.created_at::date             AS session_date
    FROM llm_token_usage u
    JOIN user_sessions s USING (session_id)
    GROUP BY s.session_id, s.user_name, s.created_at;
    """

    # ── Thesis evaluation: mode cost summary view ──────────────────────
    # Aggregates token costs by orchestration mode with estimated USD
    # pricing. Used by GET /api/analytics/token-costs and the analysis
    # notebook.  Pricing constants (as of early 2025):
    #   Gemini 2.0 Flash: $0.075 input / $0.30 output per 1M tokens
    #   GPT-4o:           $2.50  input / $10.00 output per 1M tokens
    #   Claude 3.5 Sonnet: $3.00 input / $15.00 output per 1M tokens
    mode_cost_view_ddl = """
    CREATE OR REPLACE VIEW mode_cost_summary AS
    SELECT
      ltu.orchestration_mode,
      ltu.orchestrator_model,
      ltu.synthesizer_model,
      COUNT(DISTINCT ltu.session_id)                                      AS n_sessions,
      COUNT(*)                                                            AS n_turns,
      ROUND(AVG(ltu.input_tokens + ltu.output_tokens
        + ltu.orchestrator_input_tokens + ltu.orchestrator_output_tokens)) AS avg_total_tokens,
      ROUND(AVG(jsonb_array_length(ltu.tool_calls_json)), 2)             AS avg_tool_calls,
      ROUND(AVG(
        CASE
          WHEN ltu.orchestrator_model LIKE 'gemini%'
            THEN (ltu.orchestrator_input_tokens * 0.075 + ltu.orchestrator_output_tokens * 0.30) / 1e6
          WHEN ltu.orchestrator_model LIKE 'gpt%'
            THEN (ltu.orchestrator_input_tokens * 2.50 + ltu.orchestrator_output_tokens * 10.00) / 1e6
          ELSE 0
        END
        +
        CASE
          WHEN ltu.synthesizer_model LIKE 'gemini%'
            THEN (ltu.input_tokens * 0.075 + ltu.output_tokens * 0.30) / 1e6
          WHEN ltu.synthesizer_model LIKE 'gpt%'
            THEN (ltu.input_tokens * 2.50 + ltu.output_tokens * 10.00) / 1e6
          WHEN ltu.synthesizer_model LIKE 'claude%'
            THEN (ltu.input_tokens * 3.00 + ltu.output_tokens * 15.00) / 1e6
          ELSE 0
        END
      ), 8)                                                              AS avg_usd_per_turn
    FROM llm_token_usage ltu
    WHERE ltu.call_name = 'synthesis'
    GROUP BY ltu.orchestration_mode, ltu.orchestrator_model, ltu.synthesizer_model;
    """

    path_funnel_view_ddl = """
    CREATE OR REPLACE VIEW session_path_funnel_summary AS
    WITH path_modes AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode FROM product_impressions
        UNION
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode FROM product_clicks
        UNION
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode FROM selected_items
        UNION
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode FROM product_intents
        UNION
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode FROM user_orders
    ),
    i AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS impressions
        FROM product_impressions
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    ),
    c AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS clicks
        FROM product_clicks
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    ),
    s AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS cart_adds
        FROM selected_items
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    ),
    w AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS will_buy
        FROM product_intents
        WHERE intent_type = 'will_buy'
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    ),
    n AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS not_for_me
        FROM product_intents
        WHERE intent_type = 'not_for_me'
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    ),
    o AS (
        SELECT session_id, COALESCE(path_mode, 'path1') AS path_mode, COUNT(*) AS orders
        FROM user_orders
        GROUP BY session_id, COALESCE(path_mode, 'path1')
    )
    SELECT
        pm.session_id,
        pm.path_mode,
        COALESCE(i.impressions, 0) AS impressions,
        COALESCE(c.clicks, 0) AS clicks,
        COALESCE(s.cart_adds, 0) AS cart_adds,
        COALESCE(w.will_buy, 0) AS will_buy,
        COALESCE(n.not_for_me, 0) AS not_for_me,
        COALESCE(o.orders, 0) AS orders
    FROM path_modes pm
    LEFT JOIN i ON i.session_id = pm.session_id AND i.path_mode = pm.path_mode
    LEFT JOIN c ON c.session_id = pm.session_id AND c.path_mode = pm.path_mode
    LEFT JOIN s ON s.session_id = pm.session_id AND s.path_mode = pm.path_mode
    LEFT JOIN w ON w.session_id = pm.session_id AND w.path_mode = pm.path_mode
    LEFT JOIN n ON n.session_id = pm.session_id AND n.path_mode = pm.path_mode
    LEFT JOIN o ON o.session_id = pm.session_id AND o.path_mode = pm.path_mode;
    """

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(view_ddl)
            cur.execute(mode_cost_view_ddl)
            cur.execute(path_funnel_view_ddl)
        conn.commit()


def create_session(
    user_name: str = "",
    year_of_birth: int | None = None,
    gender: str | None = None,
    preferred_model: str = "gemini-2.5-flash",
    gender_hint_enabled: bool | None = None,
    orchestration_mode: str = "direct",
) -> str:
    """Create a new session and return its ID.

    Args:
        user_name: Optional display name for the user (stored for evaluation).
        year_of_birth: Optional birth year for demographic research.
        gender: Optional gender ('male' | 'female') for demographic research.
        preferred_model: LLM chosen for the session.
        gender_hint_enabled: A/B control flag. If None, set True when gender is provided, False otherwise.
        orchestration_mode: Pipeline mode for the session ('direct' | 'react'). Default 'direct'.
    """
    session_id = str(uuid.uuid4())
    # Always enable gender filter when user declared a gender
    if gender_hint_enabled is None:
        gender_hint_enabled = (gender is not None)
    if orchestration_mode not in ("direct", "react"):
        orchestration_mode = "direct"
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions
                    (session_id, user_name, year_of_birth, gender, preferred_model,
                     gender_hint_enabled, orchestration_mode)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (session_id, user_name, year_of_birth, gender, preferred_model,
                 gender_hint_enabled, orchestration_mode),
            )
        conn.commit()
    return session_id


def get_session_orchestration_mode(session_id: str) -> str:
    """Return the orchestration_mode for a given session.

    Returns 'direct' as a safe fallback for unknown or legacy sessions.
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT orchestration_mode FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            return "direct"


def get_session_model(session_id: str) -> str:
    """Return the preferred_model for a given session."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT preferred_model FROM user_sessions WHERE session_id = %s;", (session_id,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            return "gemini-2.5-flash"


def get_session_gender(session_id: str) -> tuple[str | None, bool]:
    """Return (gender, gender_hint_enabled) for a session.

    Returns:
        Tuple of (gender str or None, gender_hint_enabled bool).
        gender is 'male', 'female', or None if not set.
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT gender, gender_hint_enabled FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()
            if row:
                return row[0], bool(row[1])
            return None, False


def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            return cur.fetchone() is not None


def add_message(session_id: str, role: str, content: str) -> None:
    """Add a message to conversation history."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_history (session_id, role, content)
                VALUES (%s, %s, %s);
                """,
                (session_id, role, content),
            )
            cur.execute(
                "UPDATE user_sessions SET updated_at = NOW() WHERE session_id = %s;",
                (session_id,),
            )
        conn.commit()


def get_history(session_id: str, limit: int = 20) -> list[Message]:
    """Retrieve recent conversation history for a session."""
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT role, content, created_at
                FROM conversation_history
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()

    messages = [
        Message(
            role=r["role"],
            content=r["content"],
            timestamp=str(r["created_at"]),
        )
        for r in reversed(rows)  # chronological order
    ]
    return messages


# ---------------------------------------------------------------------------
# Memory Agent: preference tracking
# ---------------------------------------------------------------------------


def log_query(
    session_id: str,
    query: str,
    intent: str,
    filters: dict,
) -> None:
    """Append a query entry to the session's query_history JSONB array."""
    entry = json.dumps({
        "query": query,
        "intent": intent,
        "filters": filters,
        "timestamp": datetime.now().isoformat(),
    })
    with _db_conn() as conn:
        with conn.cursor() as cur:
            # Append to JSONB array, keep last 100 entries
            cur.execute(
                """
                UPDATE user_sessions
                SET query_history = (
                    SELECT jsonb_agg(elem)
                    FROM (
                        SELECT elem
                        FROM jsonb_array_elements(
                            query_history || %s::jsonb
                        ) AS elem
                        ORDER BY elem->>'timestamp' DESC
                        LIMIT 100
                    ) sub
                ),
                updated_at = NOW()
                WHERE session_id = %s;
                """,
                (entry, session_id),
            )
        conn.commit()


def add_liked_item(session_id: str, image_id: str) -> None:
    """Append an image_id to the session's liked_items JSONB array."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_sessions
                SET liked_items = liked_items || %s::jsonb,
                    updated_at = NOW()
                WHERE session_id = %s
                AND NOT liked_items @> %s::jsonb;
                """,
                (json.dumps(image_id), session_id, json.dumps(image_id)),
            )
        conn.commit()


def get_preferences(session_id: str) -> dict:
    """Analyze query_history and liked_items to extract user preferences.

    Returns dict like:
        {
            "preferred_colors": ["white", "navy"],
            "preferred_categories": ["Shirt", "Dress"],
            "preferred_styles": ["formal"],
        }
    """
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT query_history, liked_items FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()

    if not row:
        return {}

    query_history = row["query_history"] or []
    # liked_items = row["liked_items"] or []  # Future: correlate with product data

    # Aggregate filters from query history
    color_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    style_counts: dict[str, int] = {}

    for entry in query_history:
        if not isinstance(entry, dict):
            continue
        filters = entry.get("filters", {})
        if not isinstance(filters, dict):
            continue

        color = filters.get("color", "").strip()
        if color:
            color_counts[color] = color_counts.get(color, 0) + 1

        category = filters.get("category", "").strip()
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1

        style = filters.get("style", "").strip()
        if style:
            style_counts[style] = style_counts.get(style, 0) + 1

    # Get top 3 of each
    def top_n(counts: dict[str, int], n: int = 3) -> list[str]:
        return [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])[:n]]

    result = {}
    if color_counts:
        result["preferred_colors"] = top_n(color_counts)
    if category_counts:
        result["preferred_categories"] = top_n(category_counts)
    if style_counts:
        result["preferred_styles"] = top_n(style_counts)

    return result


# ---------------------------------------------------------------------------
# Product Selection: save/get confirmed selections
# ---------------------------------------------------------------------------


def save_selected_items(session_id: str, items: list[dict]) -> int:
    """Save confirmed product selections to the database.

    Uses INSERT ... ON CONFLICT DO NOTHING to skip duplicates.
    Returns the count of newly inserted rows.
    """
    if not items:
        return 0

    inserted = 0
    with _db_conn() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO selected_items
                        (session_id, image_id, label, color, caption, image_path, search_query, position, path_mode)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, image_id, path_mode) DO NOTHING;
                    """,
                    (
                        session_id,
                        item.get("image_id", ""),
                        item.get("label", ""),
                        item.get("color", ""),
                        item.get("caption", ""),
                        item.get("image_path", ""),
                        item.get("search_query", ""),
                        item.get("position", 0),
                        item.get("path_mode", "path1"),
                    ),
                )
                inserted += cur.rowcount  # 1 if inserted, 0 if conflict
        conn.commit()
    return inserted


def get_selected_items(session_id: str) -> list[dict]:
    """Retrieve all selected items for a session, ordered by selection time."""
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT image_id, label, color, caption, image_path,
                       search_query, path_mode, selected_at
                FROM selected_items
                WHERE session_id = %s
                ORDER BY selected_at ASC;
                """,
                (session_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "image_id": r["image_id"],
            "label": r["label"],
            "color": r["color"],
            "caption": r["caption"],
            "image_path": r["image_path"],
            "search_query": r["search_query"],
            "path_mode": r["path_mode"],
            "selected_at": str(r["selected_at"]),
        }
        for r in rows
    ]


def log_cart_removal(session_id: str, image_id: str) -> bool:
    """Remove item from selections and log the cart removal event."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            # First, check if the item actually exists
            cur.execute(
                "SELECT id FROM selected_items WHERE session_id = %s AND image_id = %s;",
                (session_id, image_id)
            )
            if not cur.fetchone():
                return False

            # Delete it
            cur.execute(
                "DELETE FROM selected_items WHERE session_id = %s AND image_id = %s;",
                (session_id, image_id)
            )
            # Log the removal
            cur.execute(
                "INSERT INTO cart_removals (session_id, image_id) VALUES (%s, %s);",
                (session_id, image_id)
            )
        conn.commit()
    return True


# ---------------------------------------------------------------------------
# LLM Token Tracking
# ---------------------------------------------------------------------------


def log_token_usage(
    session_id: str,
    call_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    orchestration_mode: str = "direct",
    orchestrator_model: str = "fixed",
    synthesizer_model: str | None = None,
    tool_calls_json: list | None = None,
    orchestrator_input_tokens: int = 0,
    orchestrator_output_tokens: int = 0,
) -> None:
    """Persist one LLM call's token counts + orchestration metadata to the database.

    This is intentionally fire-and-log — callers should wrap in try/except
    so a DB error never disrupts the chat stream.

    Args:
        orchestration_mode: 'direct' for Mode A, 'agentic' for Modes B/C.
        orchestrator_model: Model ID used as orchestrator, or 'fixed' for Mode A.
        synthesizer_model: Model ID used for synthesis (if different from model_name).
        tool_calls_json: List of tool call dicts [{tool, args, result_count, duration_ms}].
        orchestrator_input_tokens: Token count for orchestrator calls (Modes B/C).
        orchestrator_output_tokens: Token count for orchestrator calls (Modes B/C).
    """
    import json as _json
    tool_calls_str = _json.dumps(tool_calls_json or [])
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_token_usage
                    (session_id, call_name, model_name, input_tokens, output_tokens,
                     orchestration_mode, orchestrator_model, synthesizer_model,
                     tool_calls_json, orchestrator_input_tokens, orchestrator_output_tokens)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s);
                """,
                (
                    session_id, call_name, model_name, input_tokens, output_tokens,
                    orchestration_mode, orchestrator_model, synthesizer_model or model_name,
                    tool_calls_str, orchestrator_input_tokens, orchestrator_output_tokens,
                ),
            )
        conn.commit()


def get_token_analytics() -> list[dict]:
    """Return per-session token aggregates ordered by date and total tokens.

    Reads the session_token_summary view.
    Returns a list of dicts with keys:
      session_id, user_name, model_name,
      total_input_tokens, total_output_tokens, total_tokens, session_date.
    """
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT session_id, user_name, model_name,
                       total_input_tokens, total_output_tokens,
                       total_tokens, session_date
                FROM session_token_summary
                ORDER BY session_date DESC, total_tokens DESC;
                """
            )
            rows = cur.fetchall()
    return [
        {
            "session_id": r["session_id"],
            "user_name": r["user_name"] or "Anonymous",
            "model_name": r["model_name"] or "",
            "total_input_tokens": r["total_input_tokens"] or 0,
            "total_output_tokens": r["total_output_tokens"] or 0,
            "total_tokens": r["total_tokens"] or 0,
            "session_date": str(r["session_date"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Behaviour Analytics: impression / click / intent / order / funnel
# ---------------------------------------------------------------------------


def log_impression_batch(session_id: str, items: list[dict]) -> int:
    """Batch-insert product impressions shown in a search result.

    Each item dict: {image_id, search_query, position}
    Returns count of rows inserted.
    """
    if not items:
        return 0
    inserted = 0
    with _db_conn() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO product_impressions
                        (session_id, image_id, search_query, position, path_mode)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        session_id,
                        item.get("image_id", ""),
                        item.get("search_query", ""),
                        item.get("position", 0),
                        item.get("path_mode", "path1"),
                    ),
                )
                inserted += 1
        conn.commit()
    return inserted


def log_click(
    session_id: str,
    image_id: str,
    position: int,
    search_query: str = "",
    path_mode: str = "path1",
) -> None:
    """Log a product card tap (click event)."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_clicks
                    (session_id, image_id, position, search_query, path_mode)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (session_id, image_id, position, search_query, path_mode),
            )
        conn.commit()


def get_last_click_position(session_id: str, image_id: str, path_mode: str = "path1") -> int:
    """Return the position from the latest click for this image in the session."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT position FROM product_clicks
                WHERE session_id = %s AND image_id = %s AND path_mode = %s
                ORDER BY clicked_at DESC
                LIMIT 1;
                """,
                (session_id, image_id, path_mode)
            )
            row = cur.fetchone()
            return row[0] if row else 0


def log_intent(
    session_id: str,

    image_id: str,
    intent_type: str,
    reason: str = "",
    path_mode: str = "path1",
) -> None:
    """Log a purchase intent signal ('will_buy' | 'not_for_me'). Idempotent."""
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product_intents
                    (session_id, image_id, intent_type, reason, path_mode)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id, image_id, intent_type, path_mode) DO NOTHING;
                """,
                (session_id, image_id, intent_type, reason, path_mode),
            )
        conn.commit()


def save_order(session_id: str, phone: str, address: str, path_mode: str | None = None) -> int:
    """Save a simulated order and mark the session as ended by order.

    Returns the auto-generated order id.
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            if not path_mode:
                cur.execute(
                    """
                    SELECT path_mode
                    FROM selected_items
                    WHERE session_id = %s
                    ORDER BY selected_at DESC
                    LIMIT 1;
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                path_mode = row[0] if row else "path1"
            cur.execute(
                """
                INSERT INTO user_orders (session_id, phone, address, path_mode)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (session_id, phone, address, path_mode),
            )
            order_id = cur.fetchone()[0]
            cur.execute(
                """
                UPDATE user_sessions
                SET ended_at = NOW(), ended_by = 'order'
                WHERE session_id = %s;
                """,
                (session_id,),
            )
        conn.commit()
    return order_id


def get_session_funnel(session_id: str) -> dict:
    """Return full funnel stats for one session.

    Returns a dict with:
        impressions, clicks, cart_adds, will_buy, not_for_me, converted,
        ctr, cart_rate, intent_rate, precision_at_k,
        model_name, total_tokens
    """
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) FROM product_impressions WHERE session_id = %s",
                (session_id,),
            )
            impressions = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM product_clicks WHERE session_id = %s",
                (session_id,),
            )
            clicks = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM selected_items WHERE session_id = %s",
                (session_id,),
            )
            cart_adds = cur.fetchone()[0]

            cur.execute(
                """
                SELECT intent_type, COUNT(*) AS cnt
                FROM product_intents
                WHERE session_id = %s
                GROUP BY intent_type;
                """,
                (session_id,),
            )
            intents = {row["intent_type"]: row["cnt"] for row in cur.fetchall()}

            cur.execute(
                "SELECT COUNT(*) FROM user_orders WHERE session_id = %s",
                (session_id,),
            )
            converted = cur.fetchone()[0] > 0

            # Token data from existing VIEW (may be None if no tokens logged)
            cur.execute(
                """
                SELECT model_name, total_tokens
                FROM session_token_summary
                WHERE session_id = %s;
                """,
                (session_id,),
            )
            row = cur.fetchone()
            model_name = row["model_name"] if row else ""
            total_tokens = int(row["total_tokens"]) if row else 0

    will_buy = intents.get("will_buy", 0)
    not_for_me = intents.get("not_for_me", 0)
    integrity = _evaluate_funnel_integrity(
        impressions=impressions,
        clicks=clicks,
        cart_adds=cart_adds,
        will_buy=will_buy,
        not_for_me=not_for_me,
        converted=converted,
    )

    return {
        "session_id": session_id,
        "model_name": model_name,
        "total_tokens": total_tokens,
        "impressions": impressions,
        "clicks": clicks,
        "cart_adds": cart_adds,
        "will_buy": will_buy,
        "not_for_me": not_for_me,
        "converted": converted,
        "ctr": round(clicks / impressions, 3) if impressions else 0.0,
        "cart_rate": round(cart_adds / clicks, 3) if clicks else 0.0,
        "intent_rate": round(will_buy / cart_adds, 3) if cart_adds else 0.0,
        "precision_at_k": round(will_buy / impressions, 3) if impressions else 0.0,
        "integrity": integrity,
    }


def _evaluate_funnel_integrity(
    *,
    impressions: int,
    clicks: int,
    cart_adds: int,
    will_buy: int,
    not_for_me: int,
    converted: bool,
) -> dict:
    """Evaluate machine-readable integrity checks for one funnel segment."""
    issues: list[str] = []
    if clicks > 0 and impressions == 0:
        issues.append("clicks_without_impressions")
    if cart_adds > 0 and impressions == 0:
        issues.append("cart_without_impressions")
    if (will_buy + not_for_me) > 0 and cart_adds == 0:
        issues.append("intent_without_cart")
    if converted and cart_adds == 0:
        issues.append("order_without_cart")
    return {"valid": len(issues) == 0, "issues": issues}


def get_session_funnel_by_path(session_id: str) -> list[dict]:
    """Return path-segmented funnel metrics for one session."""
    with _db_conn() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT path_mode, impressions, clicks, cart_adds, will_buy, not_for_me, orders
                FROM session_path_funnel_summary
                WHERE session_id = %s
                ORDER BY path_mode;
                """,
                (session_id,),
            )
            rows = cur.fetchall()

    result: list[dict] = []
    for r in rows:
        impressions = int(r["impressions"] or 0)
        clicks = int(r["clicks"] or 0)
        cart_adds = int(r["cart_adds"] or 0)
        will_buy = int(r["will_buy"] or 0)
        not_for_me = int(r["not_for_me"] or 0)
        converted = int(r["orders"] or 0) > 0
        integrity = _evaluate_funnel_integrity(
            impressions=impressions,
            clicks=clicks,
            cart_adds=cart_adds,
            will_buy=will_buy,
            not_for_me=not_for_me,
            converted=converted,
        )
        result.append(
            {
                "path_mode": r["path_mode"] or "path1",
                "impressions": impressions,
                "clicks": clicks,
                "cart_adds": cart_adds,
                "will_buy": will_buy,
                "not_for_me": not_for_me,
                "converted": converted,
                "ctr": round(clicks / impressions, 3) if impressions else 0.0,
                "cart_rate": round(cart_adds / clicks, 3) if clicks else 0.0,
                "intent_rate": round(will_buy / cart_adds, 3) if cart_adds else 0.0,
                "precision_at_k": round(will_buy / impressions, 3) if impressions else 0.0,
                "integrity": integrity,
            }
        )
    return result
