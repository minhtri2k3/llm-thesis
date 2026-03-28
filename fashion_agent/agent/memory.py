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
            minconn=1,
            maxconn=5,
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
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
        selected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, image_id)
    );

    CREATE INDEX IF NOT EXISTS idx_selected_items_session
        ON selected_items(session_id, selected_at);

    -- Clothie Web FE: user name tracking per session
    ALTER TABLE user_sessions
        ADD COLUMN IF NOT EXISTS user_name TEXT NOT NULL DEFAULT '';

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
        s.created_at::date             AS session_date
    FROM llm_token_usage u
    JOIN user_sessions s USING (session_id)
    GROUP BY s.session_id, s.user_name, s.created_at;
    """

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(view_ddl)
        conn.commit()


def create_session(user_name: str = "") -> str:
    """Create a new session and return its ID.

    Args:
        user_name: Optional display name for the user (stored for evaluation).
    """
    session_id = str(uuid.uuid4())
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_sessions (session_id, user_name) VALUES (%s, %s);",
                (session_id, user_name),
            )
        conn.commit()
    return session_id


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
                        (session_id, image_id, label, color, caption, image_path, search_query)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, image_id) DO NOTHING;
                    """,
                    (
                        session_id,
                        item.get("image_id", ""),
                        item.get("label", ""),
                        item.get("color", ""),
                        item.get("caption", ""),
                        item.get("image_path", ""),
                        item.get("search_query", ""),
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
                       search_query, selected_at
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
            "selected_at": str(r["selected_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# LLM Token Tracking
# ---------------------------------------------------------------------------


def log_token_usage(
    session_id: str,
    call_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Persist one LLM call's token counts to the database.

    This is intentionally fire-and-log — callers should wrap in try/except
    so a DB error never disrupts the chat stream.
    """
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_token_usage
                    (session_id, call_name, model_name, input_tokens, output_tokens)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (session_id, call_name, model_name, input_tokens, output_tokens),
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
