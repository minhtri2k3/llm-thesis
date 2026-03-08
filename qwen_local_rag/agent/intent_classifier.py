"""Intent classification using Gemini LLM."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""

    intent: str  # "search", "recommend", "chat", "clarify"
    filters: dict  # extracted filters like {category, color, style}
    refined_query: str  # cleaned/preprocessed query for search


INTENT_PROMPT = """You are a fashion shopping assistant. Classify the user's message into one of these intents:

1. "search" — User wants to find specific fashion items (e.g., "tìm áo sơ mi trắng", "show me blue dresses")
2. "recommend" — User wants fashion recommendations or styling advice (e.g., "gợi ý outfit cho buổi tiệc", "what goes with a black blazer?")
3. "chat" — User is making small talk, asking about the bot, or non-fashion topics (e.g., "xin chào", "bạn là ai?")
4. "clarify" — User's request is too vague to search (e.g., "tìm đồ đẹp", "something nice")

Also extract any mentioned filters:
- category: the type of clothing (Shirt, Dress, Pants, etc.)
- color: mentioned colors
- style: mentioned style (formal, casual, street, etc.)
- occasion: mentioned occasion (office, party, date, etc.)

And provide a refined search query in English that would work well for semantic search.

Respond ONLY with valid JSON in this exact format:
{
    "intent": "search|recommend|chat|clarify",
    "filters": {"category": "", "color": "", "style": "", "occasion": ""},
    "refined_query": ""
}

User message: """


def classify_intent(
    query: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> ClassifiedIntent:
    """Classify user query into search/recommend/chat/clarify."""
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: google-generativeai. "
            "Install with `pip install google-generativeai`."
        ) from exc

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not provided.")

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)

    full_prompt = INTENT_PROMPT + query
    response = model.generate_content(full_prompt)

    try:
        # Extract JSON from response
        text = response.text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
        return ClassifiedIntent(
            intent=data.get("intent", "chat"),
            filters=data.get("filters", {}),
            refined_query=data.get("refined_query", query),
        )
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat as search if classification fails
        return ClassifiedIntent(
            intent="search",
            filters={},
            refined_query=query,
        )
