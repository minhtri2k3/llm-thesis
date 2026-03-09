"""Slot-based completeness check and targeted clarification questions."""

from __future__ import annotations

import json
import os
from typing import Optional

from agent.intent_classifier import ExtractedSlots


# ---------------------------------------------------------------------------
# Slot Completeness Check
# ---------------------------------------------------------------------------

# Slot display names for Vietnamese clarification questions
SLOT_LABELS_VI = {
    "category": "loại trang phục (áo sơ mi, váy, quần jeans...)",
    "color": "màu sắc (trắng, đen, xanh navy...)",
    "fabric": "chất liệu (cotton, linen, silk, denim...)",
    "fit": "dáng/kiểu (ôm, rộng, A-line, regular...)",
    "construction": "chi tiết (cổ bẻ, khóa kéo, cổ tròn...)",
    "aesthetic": "phong cách (casual, formal, minimalist, vintage...)",
}


def check_slot_completeness(
    slots: ExtractedSlots,
) -> tuple[bool, list[str]]:
    """Check if extracted slots meet the search threshold.

    Search threshold:
    - category is filled AND
    - color is filled AND
    - at least 3 out of 4 caption slots are filled (fabric, fit, construction, aesthetic)

    Returns:
        (is_complete, missing_slot_names)
    """
    missing = []

    if not slots.category:
        missing.append("category")
    if not slots.color:
        missing.append("color")

    caption_filled = slots.caption_slots_filled()
    caption_missing = []
    if not slots.fabric:
        caption_missing.append("fabric")
    if not slots.fit:
        caption_missing.append("fit")
    if not slots.construction:
        caption_missing.append("construction")
    if not slots.aesthetic:
        caption_missing.append("aesthetic")

    # Need at least 3/4 caption slots — only report as missing if < 3 filled
    if caption_filled < 3:
        missing.extend(caption_missing)

    is_complete = bool(slots.category) and bool(slots.color) and caption_filled >= 3
    return is_complete, missing


# ---------------------------------------------------------------------------
# Targeted Clarification Question
# ---------------------------------------------------------------------------

TARGETED_QUESTION_PROMPT = """You are a fashion shopping assistant. The user is looking for clothing but hasn't provided enough detail yet.

Based on what they've already told you and what's still missing, ask a natural, friendly clarification question.

## What the user has provided:
{filled_info}

## What is still missing:
{missing_info}

## Conversation history:
{history_text}

Rules:
1. Ask in the SAME LANGUAGE as the user's messages (Vietnamese or English).
2. Ask about ALL missing information in ONE question.
3. Give specific examples for each missing item to guide the user.
4. Keep it conversational and friendly — not like a form.
5. Do NOT repeat what the user already told you.

Respond ONLY with valid JSON:
{{
    "question": "<your clarification question>"
}}
"""


def generate_targeted_question(
    slots: ExtractedSlots,
    missing_slots: list[str],
    history: list | None = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> str:
    """Generate a targeted clarification question about specific missing slots.

    Uses Gemini to produce a natural, conversational question that asks
    specifically about the missing information slots.
    """
    # Build filled info text
    filled_parts = []
    if slots.category:
        filled_parts.append(f"Loại: {slots.category}")
    if slots.color:
        filled_parts.append(f"Màu: {slots.color}")
    if slots.fabric:
        filled_parts.append(f"Chất liệu: {slots.fabric}")
    if slots.fit:
        filled_parts.append(f"Dáng: {slots.fit}")
    if slots.construction:
        filled_parts.append(f"Chi tiết: {slots.construction}")
    if slots.aesthetic:
        filled_parts.append(f"Phong cách: {slots.aesthetic}")
    filled_info = ", ".join(filled_parts) if filled_parts else "Chưa có thông tin cụ thể."

    # Build missing info text
    missing_labels = [SLOT_LABELS_VI.get(s, s) for s in missing_slots]
    missing_info = ", ".join(missing_labels)

    # Format history
    history_lines = []
    if history:
        for msg in history[-4:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            history_lines.append(f"{role}: {content[:100]}")
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

    # Try Gemini for natural question
    try:
        import google.generativeai as genai

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            return _fallback_question(missing_slots)

        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)

        prompt = TARGETED_QUESTION_PROMPT.format(
            filled_info=filled_info,
            missing_info=missing_info,
            history_text=history_text,
        )

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
        question = data.get("question", "")
        if question:
            return question
    except Exception:
        pass

    return _fallback_question(missing_slots)


def _fallback_question(missing_slots: list[str]) -> str:
    """Generate a simple fallback question when Gemini is unavailable."""
    parts = []
    for slot in missing_slots:
        label = SLOT_LABELS_VI.get(slot, slot)
        parts.append(f"- {label}")

    return (
        "Bạn có thể cho mình biết thêm không?\n"
        + "\n".join(parts)
    )


# ---------------------------------------------------------------------------
# Slot Merging
# ---------------------------------------------------------------------------

def merge_slots(
    accumulated: ExtractedSlots,
    new: ExtractedSlots,
) -> ExtractedSlots:
    """Merge new slots into accumulated. Non-null new values override old.

    This supports multi-turn conversations where the user progressively
    provides more information.
    """
    return ExtractedSlots(
        category=new.category or accumulated.category,
        color=new.color or accumulated.color,
        fabric=new.fabric or accumulated.fabric,
        fit=new.fit or accumulated.fit,
        construction=new.construction or accumulated.construction,
        aesthetic=new.aesthetic or accumulated.aesthetic,
    )


def should_reset_slots(
    accumulated: ExtractedSlots,
    new: ExtractedSlots,
) -> bool:
    """Determine if slots should be reset (new topic detected).

    Reset when the new query has a DIFFERENT category from the accumulated one,
    indicating the user is starting a completely new search.
    """
    if not accumulated.category or not new.category:
        return False
    return (
        new.category.lower().strip() != accumulated.category.lower().strip()
    )


def compose_refined_query_from_slots(slots: ExtractedSlots) -> str:
    """Compose a rich refined query from filled slots.

    This produces a query like:
    "white cotton slim fit formal shirt"
    which aligns closely with indexed caption + metadata.
    """
    parts = []
    if slots.color:
        parts.append(slots.color)
    if slots.fabric:
        parts.append(slots.fabric)
    if slots.fit:
        parts.append(slots.fit)
    if slots.construction:
        parts.append(slots.construction)
    if slots.aesthetic:
        parts.append(slots.aesthetic)
    if slots.category:
        parts.append(slots.category)
    return " ".join(parts)
