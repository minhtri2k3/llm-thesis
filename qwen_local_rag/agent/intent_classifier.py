"""Intent classification using Gemini LLM."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""

    intent: str  # "text_search", "outfit_request", "follow_up", "out_of_scope", "unclear"
    confidence: float  # 0.0 – 1.0
    filters: dict  # extracted filters like {category, color, style}
    refined_query: str  # cleaned/preprocessed query for search


INTENT_PROMPT = """You are a fashion shopping assistant. Classify the user's message into one of these intents:

1. "text_search" — User wants to find specific fashion items (e.g., "tìm áo sơ mi trắng", "show me blue dresses")
2. "outfit_request" — User wants fashion recommendations, outfit suggestions, or styling advice (e.g., "gợi ý outfit cho buổi tiệc", "what goes with a black blazer?")
3. "follow_up" — User is following up on a previous search/recommendation (e.g., "còn màu khác không?", "rẻ hơn có không?", "cái thứ 2")
4. "out_of_scope" — User is asking about non-fashion topics (e.g., "thời tiết hôm nay", "nấu phở thế nào")
5. "unclear" — User's request is too vague to search or classify (e.g., "tìm đồ đẹp", "something nice")

Also extract any mentioned filters:
- category: the type of clothing (Shirt, Dress, Pants, etc.)
- color: mentioned colors
- style: mentioned style (formal, casual, street, etc.)
- occasion: mentioned occasion (office, party, date, etc.)

And provide a refined search query in English that would work well for semantic search.
Provide a confidence score from 0.0 to 1.0 indicating how certain you are about the classification.

## Few-shot examples:

User: "tìm áo sơ mi trắng nam"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "", "occasion": ""}}, "refined_query": "white men shirt"}}

User: "gợi ý outfit cho buổi tiệc cuối tuần"
→ {{"intent": "outfit_request", "confidence": 0.9, "filters": {{"category": "", "color": "", "style": "party", "occasion": "weekend party"}}, "refined_query": "party outfit weekend"}}

User: "còn màu xanh thì sao?"
→ {{"intent": "follow_up", "confidence": 0.85, "filters": {{"category": "", "color": "blue", "style": "", "occasion": ""}}, "refined_query": "blue variant"}}

User: "thời tiết Hà Nội hôm nay"
→ {{"intent": "out_of_scope", "confidence": 0.95, "filters": {{}}, "refined_query": ""}}

User: "tìm đồ đẹp"
→ {{"intent": "unclear", "confidence": 0.4, "filters": {{}}, "refined_query": ""}}

## Conversation history (last 4 messages):
{history_text}

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "text_search|outfit_request|follow_up|out_of_scope|unclear",
    "confidence": 0.0,
    "filters": {{"category": "", "color": "", "style": "", "occasion": ""}},
    "refined_query": ""
}}

User message: """


def classify_intent(
    query: str,
    history: list | None = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> ClassifiedIntent:
    """Classify user query into text_search/outfit_request/follow_up/out_of_scope/unclear."""
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

    # Format history (last 4 messages)
    history_lines = []
    if history:
        for msg in history[-4:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            history_lines.append(f"{role}: {content[:100]}")
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

    full_prompt = INTENT_PROMPT.format(history_text=history_text) + query
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
            intent=data.get("intent", "text_search"),
            confidence=float(data.get("confidence", 0.5)),
            filters=data.get("filters", {}),
            refined_query=data.get("refined_query", query),
        )
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat as search if classification fails
        return ClassifiedIntent(
            intent="text_search",
            confidence=0.5,
            filters={},
            refined_query=query,
        )

