"""Slot-based completeness check and targeted clarification questions."""

from __future__ import annotations


from agent.intent_classifier import ExtractedSlots


# ---------------------------------------------------------------------------
# Slot Completeness Check
# ---------------------------------------------------------------------------


def check_slot_completeness(
    slots: ExtractedSlots,
) -> tuple[bool, list[str]]:
    """Check if extracted slots meet the search threshold.

    Search threshold (updated):
    - ``category`` is filled AND
    - ``color`` is filled AND
    - at least one of ``fabric`` or ``fit`` is filled

    ``construction`` and ``aesthetic`` are *bonus* slots — the agent may
    suggest them in the response text but they never block a search.

    Returns:
        (is_complete, missing_slot_names)
    """
    missing: list[str] = []

    if not slots.category:
        missing.append("category")
    if not slots.color:
        missing.append("color")

    has_fabric_or_fit = bool(slots.fabric) or bool(slots.fit)
    if not has_fabric_or_fit:
        # Report both as missing so the template question covers both
        if not slots.fabric:
            missing.append("fabric")
        if not slots.fit:
            missing.append("fit")

    is_complete = bool(slots.category) and bool(slots.color) and has_fabric_or_fit
    return is_complete, missing


# ---------------------------------------------------------------------------
# Template-based clarification (0 LLM calls)
# ---------------------------------------------------------------------------

# Pre-built template parts — imported from centralized prompts module.
from agent.prompts import SLOT_TEMPLATES, COMBO_TEMPLATES


def build_template_question(
    missing_slots: list[str],
    slots: ExtractedSlots,
) -> str:
    """Build a clarification question from templates (0 LLM calls).

    Selects the best pre-built template based on which slots are missing,
    then interpolates any known slot values for personalisation.

    Args:
        missing_slots: List of missing slot names from ``check_slot_completeness``.
        slots: Current accumulated slot data (used for template interpolation).

    Returns:
        A friendly English clarification question string.
    """
    missing_key = frozenset(missing_slots)

    # Try exact match first, then fallback to generic build
    template = COMBO_TEMPLATES.get(missing_key)
    if template:
        return template.format(
            category=slots.category or "clothing",
            color=slots.color or "your preferred color",
        )

    # Generic fallback: list each missing slot individually
    parts = ["Could you tell me a bit more? 💬"]
    for slot in missing_slots:
        label = SLOT_TEMPLATES.get(slot, slot)
        parts.append(f"• **{slot.capitalize()}**: {label}")
    return "\n".join(parts)



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
