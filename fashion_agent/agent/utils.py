"""Shared utility helpers for the fashion agent modules.

- ``parse_llm_json``: Extract JSON from an LLM response that may be wrapped
  in markdown code‑fences.
- ``fallback_text_response``: Generate a plain‑text product summary when the
  LLM is unavailable.
- Category validation constants and helpers for unsupported category detection.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# Supported clothing categories — must match the 17 distinct label values
# in the fashion_items database table.
# ---------------------------------------------------------------------------

SUPPORTED_CATEGORIES: set[str] = {
    "Blazer", "Blouse", "Body", "Dress", "Hat", "Hoodie", "Longsleeve",
    "Outwear", "Pants", "Polo", "Shirt", "Shoes", "Shorts", "Skirt",
    "T-Shirt", "Top", "Undershirt",
}

# Common unsupported items → 2–3 supported alternatives.
# Empty list means no close equivalent exists.
UNSUPPORTED_CATEGORY_SUGGESTIONS: dict[str, list[str]] = {
    "bikini":     ["Body", "Top", "Shorts"],
    "swimsuit":   ["Body", "Shorts"],
    "swimwear":   ["Body", "Shorts", "Top"],
    "jeans":      ["Pants", "Shorts"],
    "denim":      ["Pants", "Shorts"],
    "coat":       ["Outwear", "Blazer"],
    "jacket":     ["Outwear", "Blazer", "Hoodie"],
    "cardigan":   ["Outwear", "Longsleeve"],
    "sweater":    ["Hoodie", "Longsleeve"],
    "suit":       ["Blazer", "Pants"],
    "sneakers":   ["Shoes"],
    "boots":      ["Shoes"],
    "heels":      ["Shoes"],
    "bra":        ["Body", "Undershirt"],
    "underwear":  ["Undershirt", "Body"],
    "pyjamas":    ["Undershirt", "Longsleeve"],
    "lingerie":   ["Body", "Undershirt"],
    "vest":       ["Top", "Undershirt"],
    "crop top":   ["Top", "Blouse"],
    "tank top":   ["Top", "Undershirt"],
    "turtleneck": ["Longsleeve", "Top"],
    "scarf":      ["Hat"],
    "cap":        ["Hat"],
    "bag":        [],
    "watch":      [],
}


def _find_category_suggestions(category: str) -> list[str]:
    """Find supported category suggestions for an unsupported category.

    Lookup order:
    1. Exact match (case-insensitive) in UNSUPPORTED_CATEGORY_SUGGESTIONS
    2. Fuzzy fallback via rapidfuzz against SUPPORTED_CATEGORIES (threshold ≥ 60)
    3. Empty list if no match found

    Returns at most 3 suggestions.
    """
    normalized = category.strip().lower()
    if not normalized:
        return []

    # 1. Static map lookup
    suggestions = UNSUPPORTED_CATEGORY_SUGGESTIONS.get(normalized)
    if suggestions is not None:
        return suggestions[:3]

    # 2. Fuzzy fallback
    try:
        from rapidfuzz import process
        match = process.extractOne(
            normalized,
            SUPPORTED_CATEGORIES,
            score_cutoff=60,
        )
        if match:
            return [match[0]]
    except Exception:
        pass  # rapidfuzz unavailable — degrade gracefully

    # 3. No match
    return []


def parse_llm_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from raw LLM output.

    Handles common patterns:
    - Raw JSON string
    - JSON wrapped in ```json ... ``` or ``` ... ``` code blocks
    - Leading/trailing whitespace

    Returns an empty dict on any parse failure.
    """
    cleaned = text.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        # Remove opening fence (possibly with language tag)
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        # Remove closing fence
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        # If the LLM returned a JSON array, wrap it
        if isinstance(result, list):
            return {"items": result}
    except (json.JSONDecodeError, ValueError):
        pass

    # Last resort: try to find a JSON object in the text
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    return {}


def fallback_text_response(products: list) -> str:
    """Build a simple Vietnamese text response listing products.

    Used as a fallback when the Gemini synthesis LLM is unavailable.
    Each product is expected to have a ``.label`` attribute (or be a dict
    with a ``label`` key).
    """
    if not products:
        return "No matching products found."

    labels: list[str] = []
    for p in products[:5]:
        if hasattr(p, "label"):
            labels.append(p.label)
        elif isinstance(p, dict):
            labels.append(p.get("label", "Unknown"))
        else:
            labels.append(str(p))

    return f"Tìm thấy {len(products)} sản phẩm: {', '.join(labels)}."


def format_history_text(
    history: list | None,
    limit: int = 4,
    truncate: int = 100,
) -> str:
    """Format conversation history into text for prompt context.

    Shared helper used by intent classification, clarification gate,
    and synthesis context builder — replacing 3 copy-pasted blocks.

    Args:
        history:  List of message objects (with ``.role`` and ``.content``).
        limit:    Number of recent messages to include.
        truncate: Max characters per message content.

    Returns:
        Formatted history text, or ``"No prior conversation."`` if empty.
    """
    if not history:
        return "No prior conversation."

    lines: list[str] = []
    for msg in history[-limit:]:
        role = getattr(msg, "role", "user")
        content = getattr(msg, "content", str(msg))
        lines.append(f"{role}: {content[:truncate]}")
    return "\n".join(lines) if lines else "No prior conversation."
