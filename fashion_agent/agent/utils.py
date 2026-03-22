"""Shared utility helpers for the fashion agent modules.

- ``parse_llm_json``: Extract JSON from an LLM response that may be wrapped
  in markdown code‑fences.
- ``fallback_text_response``: Generate a plain‑text product summary when the
  LLM is unavailable.
"""

from __future__ import annotations

import json
import re
from typing import Any


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
