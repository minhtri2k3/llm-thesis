"""Intent classification with slot extraction using Gemini LLM."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedSlots:
    """6 information slots extracted from user query.

    Aligned with caption generation structure:
    - category/color: metadata fields
    - fabric/fit/construction/aesthetic: 4 caption properties
    """

    category: Optional[str] = None  # e.g., "Shirt", "Dress", "Pants"
    color: Optional[str] = None  # e.g., "white", "navy blue"
    fabric: Optional[str] = None  # e.g., "cotton", "silk", "denim"
    fit: Optional[str] = None  # e.g., "slim fit", "oversized", "A-line"
    construction: Optional[str] = None  # e.g., "point collar", "zip closure"
    aesthetic: Optional[str] = None  # e.g., "casual", "formal", "minimalist"

    def filled_count(self) -> int:
        """Count how many slots are filled (non-null, non-empty)."""
        return sum(1 for v in self._all_values() if v)

    def caption_slots_filled(self) -> int:
        """Count filled caption slots (fabric, fit, construction, aesthetic)."""
        return sum(1 for v in [self.fabric, self.fit, self.construction, self.aesthetic] if v)

    def missing_slots(self) -> list[str]:
        """Return names of missing slots."""
        missing = []
        if not self.category:
            missing.append("category")
        if not self.color:
            missing.append("color")
        if not self.fabric:
            missing.append("fabric")
        if not self.fit:
            missing.append("fit")
        if not self.construction:
            missing.append("construction")
        if not self.aesthetic:
            missing.append("aesthetic")
        return missing

    def _all_values(self) -> list[Optional[str]]:
        return [self.category, self.color, self.fabric, self.fit, self.construction, self.aesthetic]


@dataclass
class ClassifiedIntent:
    """Result of intent classification with extracted slots."""

    intent: str  # "text_search", "outfit_request", "follow_up", "out_of_scope", "unclear"
    confidence: float  # 0.0 – 1.0
    filters: dict  # extracted filters like {category, color, style}
    refined_query: str  # cleaned/preprocessed query for search
    extracted_slots: ExtractedSlots = field(default_factory=ExtractedSlots)


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

AND extract these 6 detailed slots from the user's query:
- slot_category: specific type of clothing (e.g., "Shirt", "Dress", "Jacket", "Pants")
- slot_color: specific color (e.g., "white", "navy blue", "red with stripes")
- slot_fabric: material/texture (e.g., "cotton", "silk", "denim", "chiffon", "linen")
- slot_fit: silhouette/fit (e.g., "slim fit", "oversized", "A-line", "relaxed fit", "regular")
- slot_construction: construction details (e.g., "point collar", "zip closure", "button-down", "crew neck", "v-neck")
- slot_aesthetic: overall style/aesthetic (e.g., "casual", "formal", "minimalist", "vintage", "streetwear")

Set each slot to "" if the user did NOT mention that information.

And provide a refined search query in English that would work well for semantic search.
Provide a confidence score from 0.0 to 1.0 indicating how certain you are about the classification.

## Few-shot examples:

User: "tìm áo sơ mi trắng cotton, dáng slim fit, phong cách minimalist"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "minimalist", "occasion": ""}}, "refined_query": "white cotton slim fit minimalist shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "cotton", "slot_fit": "slim fit", "slot_construction": "", "slot_aesthetic": "minimalist"}}

User: "tìm áo sơ mi trắng nam"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "", "occasion": ""}}, "refined_query": "white men shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "gợi ý outfit cho buổi tiệc cuối tuần"
→ {{"intent": "outfit_request", "confidence": 0.9, "filters": {{"category": "", "color": "", "style": "party", "occasion": "weekend party"}}, "refined_query": "party outfit weekend", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "party"}}

User: "còn màu xanh thì sao?"
→ {{"intent": "follow_up", "confidence": 0.85, "filters": {{"category": "", "color": "blue", "style": "", "occasion": ""}}, "refined_query": "blue variant", "slot_category": "", "slot_color": "blue", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "thời tiết Hà Nội hôm nay"
→ {{"intent": "out_of_scope", "confidence": 0.95, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "tìm đồ đẹp"
→ {{"intent": "unclear", "confidence": 0.4, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

## Conversation history (last 4 messages):
{history_text}

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "text_search|outfit_request|follow_up|out_of_scope|unclear",
    "confidence": 0.0,
    "filters": {{"category": "", "color": "", "style": "", "occasion": ""}},
    "refined_query": "",
    "slot_category": "",
    "slot_color": "",
    "slot_fabric": "",
    "slot_fit": "",
    "slot_construction": "",
    "slot_aesthetic": ""
}}

User message: """


def _parse_slots(data: dict) -> ExtractedSlots:
    """Parse extracted slots from Gemini JSON response with fallback."""
    try:
        return ExtractedSlots(
            category=data.get("slot_category") or None,
            color=data.get("slot_color") or None,
            fabric=data.get("slot_fabric") or None,
            fit=data.get("slot_fit") or None,
            construction=data.get("slot_construction") or None,
            aesthetic=data.get("slot_aesthetic") or None,
        )
    except Exception:
        return ExtractedSlots()


def classify_intent(
    query: str,
    history: list | None = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> ClassifiedIntent:
    """Classify user query and extract 6 information slots in a single LLM call."""
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

        slots = _parse_slots(data)

        return ClassifiedIntent(
            intent=data.get("intent", "text_search"),
            confidence=float(data.get("confidence", 0.5)),
            filters=data.get("filters", {}),
            refined_query=data.get("refined_query", query),
            extracted_slots=slots,
        )
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat as search if classification fails, with empty slots
        return ClassifiedIntent(
            intent="text_search",
            confidence=0.5,
            filters={},
            refined_query=query,
            extracted_slots=ExtractedSlots(),
        )
