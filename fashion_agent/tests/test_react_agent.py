"""Unit tests for react_agent module.

Run from fashion_agent/ directory:
    pytest tests/test_react_agent.py -v
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


@dataclass
class _MockClassifiedIntent:
    intent: str
    confidence: float
    refined_query: str = "test query"
    filters: dict = field(default_factory=dict)
    input_tokens: int = 10
    output_tokens: int = 5

    # Stub for ExtractedSlots
    @property
    def extracted_slots(self):
        return None


@dataclass
class _MockToolCall:
    tool: str
    args: dict = field(default_factory=dict)
    result_count: int = 3
    duration_ms: float = 120.0

    def to_dict(self):
        return {"tool": self.tool, "args": self.args, "result_count": self.result_count, "duration_ms": self.duration_ms}


@dataclass
class _MockOrchResult:
    products: list = field(default_factory=list)
    tool_results_text: str = "(results)"
    tool_calls: list = field(default_factory=list)
    orchestrator_input_tokens: int = 50
    orchestrator_output_tokens: int = 25
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Tests for _react_gate()
# ---------------------------------------------------------------------------


def test_gate_blocks_out_of_scope():
    """_react_gate returns False for intent='out_of_scope'."""
    from agent.react_agent import _react_gate

    classified = _MockClassifiedIntent(intent="out_of_scope", confidence=0.9)
    assert _react_gate(classified) is False


def test_gate_blocks_unclear():
    """_react_gate returns False for intent='unclear'."""
    from agent.react_agent import _react_gate

    classified = _MockClassifiedIntent(intent="unclear", confidence=0.8)
    assert _react_gate(classified) is False


def test_gate_blocks_low_confidence():
    """_react_gate returns False when confidence < REACT_CONFIDENCE_THRESHOLD (0.50)."""
    from agent.react_agent import _react_gate

    classified = _MockClassifiedIntent(intent="text_search", confidence=0.35)
    assert _react_gate(classified) is False


def test_gate_blocks_at_threshold():
    """_react_gate returns False when confidence == threshold (exclusive boundary)."""
    from agent.react_agent import REACT_CONFIDENCE_THRESHOLD, _react_gate

    classified = _MockClassifiedIntent(intent="text_search", confidence=REACT_CONFIDENCE_THRESHOLD - 0.01)
    assert _react_gate(classified) is False


def test_gate_passes_valid_intent():
    """_react_gate returns True for a clear intent with high confidence."""
    from agent.react_agent import _react_gate

    classified = _MockClassifiedIntent(intent="text_search", confidence=0.85)
    assert _react_gate(classified) is True


def test_gate_passes_outfit_request():
    """_react_gate returns True for outfit_request at sufficient confidence."""
    from agent.react_agent import _react_gate

    classified = _MockClassifiedIntent(intent="outfit_request", confidence=0.70)
    assert _react_gate(classified) is True


def test_gate_passes_at_threshold():
    """_react_gate returns True when confidence == REACT_CONFIDENCE_THRESHOLD."""
    from agent.react_agent import REACT_CONFIDENCE_THRESHOLD, _react_gate

    classified = _MockClassifiedIntent(intent="text_search", confidence=REACT_CONFIDENCE_THRESHOLD)
    assert _react_gate(classified) is True


# ---------------------------------------------------------------------------
# Tests for _log_react_traces()
# ---------------------------------------------------------------------------


def test_react_traces_logged():
    """_log_react_traces inserts correct number of rows (one per tool call)."""
    from agent.react_agent import _log_react_traces

    tool_calls = [
        _MockToolCall(tool="search_fashion", args={"query": "white shirt"}, result_count=5),
        _MockToolCall(tool="recommend_outfit", args={"style": "casual"}, result_count=3),
    ]
    orch_result = _MockOrchResult(tool_calls=tool_calls)

    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    with patch("agent.react_agent._db_conn", return_value=mock_conn):
        _log_react_traces("session-123", "white shirt", orch_result)

    # Should have called cur.execute twice (once per tool call)
    assert mock_cursor.execute.call_count == 2


def test_react_traces_skipped_when_no_tool_calls():
    """_log_react_traces does nothing when there are no tool calls."""
    from agent.react_agent import _log_react_traces

    orch_result = _MockOrchResult(tool_calls=[])

    with patch("agent.react_agent._db_conn") as mock_db:
        _log_react_traces("session-123", "query", orch_result)
        mock_db.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for chat() (integration-style with mocks)
# ---------------------------------------------------------------------------


def test_chat_returns_agent_response():
    """chat() returns AgentResponse with correct structure."""
    from agent.react_agent import chat

    mock_classified = _MockClassifiedIntent(intent="text_search", confidence=0.85)
    mock_products = [
        {"image_id": "img_001", "image_path": "/img/001.jpg", "label": "White Shirt",
         "color": "white", "caption": "A slim fit white shirt", "score": 0.9},
    ]
    mock_orch = _MockOrchResult(
        products=mock_products,
        tool_calls=[_MockToolCall(tool="search_fashion", result_count=1)],
    )

    with (
        patch("agent.react_agent.session_exists", return_value=True),
        patch("agent.react_agent.get_session_model", return_value="gemini-2.5-flash"),
        patch("agent.react_agent.add_message"),
        patch("agent.react_agent.get_history", return_value=[]),
        patch("agent.react_agent.classify_intent", return_value=mock_classified),
        patch("agent.react_agent.orchestrate_with_gemini", return_value=mock_orch),
        patch("agent.react_agent._log_react_traces"),
        patch("agent.react_agent.get_session_gender", return_value=(None, False)),
        patch("agent.react_agent.log_token_usage"),
        patch("agent.react_agent.get_client") as mock_get_client,
        patch("agent.react_agent.parse_llm_json", return_value={"answer": "Here are shirts", "styling_suggestion": ""}),
    ):
        mock_client = MagicMock()
        mock_client.generate.return_value = '{"answer": "Here are shirts", "styling_suggestion": ""}'
        mock_get_client.return_value = mock_client

        response = chat("white shirt for men", session_id="session-abc")

    assert response.answer == "Here are shirts"
    assert response.intent == "text_search"
    assert response.session_id == "session-abc"
    assert len(response.products) == 1
    assert response.products[0].image_id == "img_001"


def test_chat_gate_blocks_out_of_scope():
    """chat() returns out-of-scope message without calling orchestrate_with_gemini."""
    from agent.react_agent import chat

    mock_classified = _MockClassifiedIntent(intent="out_of_scope", confidence=0.95)

    with (
        patch("agent.react_agent.session_exists", return_value=True),
        patch("agent.react_agent.get_session_model", return_value="gemini-2.5-flash"),
        patch("agent.react_agent.add_message"),
        patch("agent.react_agent.get_history", return_value=[]),
        patch("agent.react_agent.classify_intent", return_value=mock_classified),
        patch("agent.react_agent.orchestrate_with_gemini") as mock_orch,
        patch("agent.react_agent.log_token_usage"),
        patch("agent.react_agent.get_client") as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response = chat("what is the weather?", session_id="session-abc")

    # Should NOT have called the orchestrator
    mock_orch.assert_not_called()
    assert "fashion" in response.answer.lower() or "thời trang" in response.answer.lower()
    assert response.products == []
