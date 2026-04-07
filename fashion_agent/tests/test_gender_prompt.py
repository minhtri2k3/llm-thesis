"""Test Task 8.2 — verify gender-aware prompting.

Tests that:
- When `gender_hint_enabled=True` and gender is set, the synthesis prompt
  contains a gender context block.
- When `gender_hint_enabled=False` or gender is None, the prompt has no
  gender mention.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.fashion_agent import _build_synthesis_context
from agent.memory import Message


def _make_history():
    return [Message(role="user", content="I want a shirt", timestamp="2024-01-01T00:00:00")]


def _make_products():
    """Return lightweight mock products that have .label, .color, .caption attributes."""
    class FakeProduct:
        def __init__(self, label, color, caption):
            self.label = label
            self.color = color
            self.caption = caption
            self.image_id = "img_1"
            self.image_path = "/img/1.jpg"
            self.score = 0.9
    return [FakeProduct("Blue Shirt", "blue", "A nice casual shirt")]


class TestGenderAwarePrompting:
    def test_gender_context_injected_when_hint_enabled_male(self):
        """Gender context block should appear when hint is enabled + gender=male."""
        with patch("agent.fashion_agent.get_session_gender") as mock_gender:
            mock_gender.return_value = ("male", True)
            ctx = _build_synthesis_context(
                query="show me shirts",
                products=_make_products(),
                history=_make_history(),
                preferences={},
                session_id="test-session-123",
            )
        assert "gender_context" in ctx
        assert "male" in ctx["gender_context"]
        assert "menswear" in ctx["gender_context"]

    def test_gender_context_injected_when_hint_enabled_female(self):
        """Gender context block should appear when hint is enabled + gender=female."""
        with patch("agent.fashion_agent.get_session_gender") as mock_gender:
            mock_gender.return_value = ("female", True)
            ctx = _build_synthesis_context(
                query="show me dresses",
                products=_make_products(),
                history=_make_history(),
                preferences={},
                session_id="test-session-456",
            )
        assert "gender_context" in ctx
        assert "female" in ctx["gender_context"]
        assert "womenswear" in ctx["gender_context"]

    def test_no_gender_context_when_hint_disabled(self):
        """Gender context should be empty when hint is disabled (control group)."""
        with patch("agent.fashion_agent.get_session_gender") as mock_gender:
            mock_gender.return_value = ("male", False)  # hint disabled
            ctx = _build_synthesis_context(
                query="show me shirts",
                products=_make_products(),
                history=_make_history(),
                preferences={},
                session_id="test-session-789",
            )
        assert ctx["gender_context"] == ""

    def test_no_gender_context_when_gender_is_none(self):
        """Gender context should be empty when gender is not set."""
        with patch("agent.fashion_agent.get_session_gender") as mock_gender:
            mock_gender.return_value = (None, True)  # hint enabled but no gender
            ctx = _build_synthesis_context(
                query="show me casual outfits",
                products=_make_products(),
                history=_make_history(),
                preferences={},
                session_id="test-session-999",
            )
        assert ctx["gender_context"] == ""

    def test_no_gender_context_when_no_session_id(self):
        """Gender context should be empty when no session_id is passed."""
        ctx = _build_synthesis_context(
            query="show me shirts",
            products=_make_products(),
            history=_make_history(),
            preferences={},
            session_id=None,  # no session
        )
        assert ctx["gender_context"] == ""

    def test_gender_context_not_in_prompt_when_empty(self):
        """An empty gender_context injected into the prompt should produce no gender text."""
        from agent.prompts import STREAM_SYNTHESIS_PROMPT
        from agent.memory import Message

        ctx = {
            "language": "English",
            "gender_context": "",
            "products_text": "1. Blue Shirt | Color: blue | Caption: Nice shirt",
            "history_text": "User: show shirts",
            "preferences_text": "No preferences yet.",
            "num_results": 1,
            "cta_example": "👉 Type a number (1-1) to select your favorite!",
        }
        prompt = STREAM_SYNTHESIS_PROMPT.format(query="show shirts", **ctx)
        assert "gender" not in prompt.lower() or "gender_context" not in prompt

    def test_synthesis_context_keys_complete(self):
        """_build_synthesis_context should always return all required keys."""
        with patch("agent.fashion_agent.get_session_gender") as mock_gender:
            mock_gender.return_value = ("female", True)
            ctx = _build_synthesis_context(
                query="formal dresses",
                products=_make_products(),
                history=_make_history(),
                preferences={"preferred_colors": ["red", "blue"]},
                session_id="test-complete",
            )
        required_keys = {"products_text", "history_text", "preferences_text",
                         "language", "gender_context", "num_results", "cta_example"}
        assert required_keys.issubset(set(ctx.keys()))
