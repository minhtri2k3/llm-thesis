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
