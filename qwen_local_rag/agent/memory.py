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


def _get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "fashion_rag"),
        user=os.getenv("PGUSER", "fashion_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


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
    """
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_sessions (session_id) VALUES (%s);",
                (session_id,),
            )
        conn.commit()
    finally:
        conn.close()
    return session_id


def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def add_message(session_id: str, role: str, content: str) -> None:
    """Add a message to conversation history."""
    conn = _get_connection()
    try:
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
    finally:
        conn.close()


def get_history(session_id: str, limit: int = 20) -> list[Message]:
    """Retrieve recent conversation history for a session."""
    conn = _get_connection()
    try:
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
    finally:
        conn.close()

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
    conn = _get_connection()
    try:
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
    finally:
        conn.close()


def add_liked_item(session_id: str, image_id: str) -> None:
    """Append an image_id to the session's liked_items JSONB array."""
    conn = _get_connection()
    try:
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
    finally:
        conn.close()


def get_preferences(session_id: str) -> dict:
    """Analyze query_history and liked_items to extract user preferences.

    Returns dict like:
        {
            "preferred_colors": ["white", "navy"],
            "preferred_categories": ["Shirt", "Dress"],
            "preferred_styles": ["formal"],
        }
    """
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT query_history, liked_items FROM user_sessions WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

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

