"""Intent classification with slot extraction using Gemini LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agent.utils import parse_llm_json
from agent.utils import format_history_text
from agent.prompts import INTENT_PROMPT
from shared.llm import get_model


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
) -> ClassifiedIntent:
    """Classify user query and extract 6 information slots in a single LLM call."""
    model = get_model()

    history_text = format_history_text(history, limit=4)

    full_prompt = INTENT_PROMPT.format(history_text=history_text) + query
    response = model.generate_content(full_prompt)

    try:
        data = parse_llm_json(response.text)
        slots = _parse_slots(data)

        return ClassifiedIntent(
            intent=data.get("intent", "text_search"),
            confidence=float(data.get("confidence", 0.5)),
            filters=data.get("filters", {}),
            refined_query=data.get("refined_query", query),
            extracted_slots=slots,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Intent classification parse failed: %s", exc)
        # Fallback: treat as search if classification fails, with empty slots
        return ClassifiedIntent(
            intent="text_search",
            confidence=0.5,
            filters={},
            refined_query=query,
            extracted_slots=ExtractedSlots(),
        )
