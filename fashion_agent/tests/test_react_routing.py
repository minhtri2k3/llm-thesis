"""API routing tests: dispatch to correct agent based on session orchestration_mode.

Run from fashion_agent/ directory:
    pytest tests/test_react_routing.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests for get_session_orchestration_mode()
# ---------------------------------------------------------------------------


def test_get_session_orchestration_mode_direct():
    """Returns 'direct' for a session created in direct mode."""
    from agent.memory import get_session_orchestration_mode

    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = ("direct",)

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    with patch("agent.memory._db_conn", return_value=mock_conn):
        result = get_session_orchestration_mode("session-direct")

    assert result == "direct"


def test_get_session_orchestration_mode_react():
    """Returns 'react' for a session created in react mode."""
    from agent.memory import get_session_orchestration_mode

    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = ("react",)

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    with patch("agent.memory._db_conn", return_value=mock_conn):
        result = get_session_orchestration_mode("session-react")

    assert result == "react"


def test_get_session_orchestration_mode_fallback():
    """Returns 'direct' as fallback for unknown session (None row)."""
    from agent.memory import get_session_orchestration_mode

    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = None  # session not found

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    with patch("agent.memory._db_conn", return_value=mock_conn):
        result = get_session_orchestration_mode("nonexistent-session")

    assert result == "direct"


# ---------------------------------------------------------------------------
# Tests for API routing dispatch
# ---------------------------------------------------------------------------


def test_direct_session_routes_to_fashion_agent():
    """POST /api/chat/stream routes to fashion_agent.chat_stream for 'direct' mode."""
    from fastapi.testclient import TestClient

    with (
        patch("agent.memory.get_session_orchestration_mode", return_value="direct"),
        patch("agent.fashion_agent.chat_stream") as mock_direct_stream,
        patch("agent.react_agent.chat_stream") as mock_react_stream,
    ):
        # mock_direct_stream must return an iterable
        mock_direct_stream.return_value = iter([
            'event: done\ndata: {"session_id": "s1", "intent": "text_search", "styling": ""}\n\n'
        ])

        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/api/chat/stream",
            json={"message": "white shirt", "session_id": "session-direct"},
        )

    mock_direct_stream.assert_called_once()
    mock_react_stream.assert_not_called()


def test_react_session_routes_to_react_agent():
    """POST /api/chat/stream routes to react_agent.chat_stream for 'react' mode."""
    with (
        patch("agent.memory.get_session_orchestration_mode", return_value="react"),
        patch("agent.react_agent.chat_stream") as mock_react_stream,
        patch("agent.fashion_agent.chat_stream") as mock_direct_stream,
    ):
        mock_react_stream.return_value = iter([
            'event: done\ndata: {"session_id": "s2", "intent": "text_search", "styling": "", "orchestration_mode": "react"}\n\n'
        ])

        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.post(
            "/api/chat/stream",
            json={"message": "white shirt", "session_id": "session-react"},
        )

    mock_react_stream.assert_called_once()
    mock_direct_stream.assert_not_called()


def test_unknown_mode_defaults_to_direct():
    """GET /api/chat/stream falls back to direct when mode lookup returns 'direct' (default)."""
    with (
        patch("agent.memory.get_session_orchestration_mode", return_value="direct"),
        patch("agent.fashion_agent.chat_stream") as mock_direct_stream,
        patch("agent.react_agent.chat_stream") as mock_react_stream,
    ):
        mock_direct_stream.return_value = iter([
            'event: done\ndata: {"session_id": "s3", "intent": "text_search", "styling": ""}\n\n'
        ])

        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Pass empty session_id — should still route to direct as safe fallback
        response = client.post(
            "/api/chat/stream",
            json={"message": "shirt", "session_id": ""},
        )

    mock_direct_stream.assert_called_once()
    mock_react_stream.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for CreateSessionRequest validation
# ---------------------------------------------------------------------------


def test_create_session_valid_direct():
    """POST /api/sessions accepts orchestration_mode='direct'."""
    from fastapi.testclient import TestClient

    with patch("agent.memory.create_session", return_value="new-session-id"):
        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/api/sessions",
            json={
                "user_name": "Test User",
                "year_of_birth": 2000,
                "gender": "male",
                "preferred_model": "gemini-2.5-flash",
                "orchestration_mode": "direct",
            },
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "new-session-id"


def test_create_session_valid_react():
    """POST /api/sessions accepts orchestration_mode='react'."""
    from fastapi.testclient import TestClient

    with patch("agent.memory.create_session", return_value="new-react-session-id"):
        from api.main import app
        client = TestClient(app)

        response = client.post(
            "/api/sessions",
            json={
                "user_name": "Test User",
                "year_of_birth": 1995,
                "gender": "female",
                "preferred_model": "gemini-2.5-flash",
                "orchestration_mode": "react",
            },
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "new-react-session-id"


def test_create_session_invalid_mode():
    """POST /api/sessions rejects invalid orchestration_mode."""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/sessions",
        json={
            "user_name": "Test",
            "year_of_birth": 2000,
            "gender": "male",
            "preferred_model": "gemini-2.5-flash",
            "orchestration_mode": "invalid_mode",
        },
    )

    assert response.status_code in (422, 500)  # validation error
