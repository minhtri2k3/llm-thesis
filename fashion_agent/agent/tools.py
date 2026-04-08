"""Tool functions exposed to the agentic orchestrators (Mode B and Mode C).

These are thin wrappers around the existing search engine that return
plain dicts instead of NodeWithScore objects, making them easy to serialize
and pass through LLM function calling.
"""
from __future__ import annotations

import logging
from typing import Optional

from agent.utils import SUPPORTED_CATEGORIES, _find_category_suggestions

logger = logging.getLogger(__name__)


def run_search_tool(
    query: str,
    top_k: int = 5,
    gender: str = "",
    category: str = "",
    color: str = "",
) -> list[dict]:
    """Execute a hybrid fashion search and return plain dicts.

    Args:
        query: Natural language search query.
        top_k: Max number of results.
        gender: Optional gender filter ('male', 'female', 'unisex', '').
        category: Optional category filter.
        color: Optional color filter.

    Returns:
        List of product dicts with keys: image_id, image_path, label, color, caption, score.
        If category is unsupported, returns error dict instead.
    """
    from search.search_engine import search as hybrid_search

    # ── Safety-net: reject unsupported categories ──────────────────────
    if category and category not in SUPPORTED_CATEGORIES:
        suggestions = _find_category_suggestions(category)
        return [{
            "__error__": "unsupported_category",
            "requested": category,
            "suggestions": suggestions,
        }]

    filters: dict[str, str] = {}
    if gender and gender not in ("", "unisex"):
        filters["gender"] = gender
    if category:
        filters["category"] = category
    if color:
        filters["color"] = color

    try:
        results = hybrid_search(query, top_k=top_k, use_query_expansion=False, filters=filters)
        return [
            {
                "image_id": r.image_id,
                "image_path": r.image_path,
                "label": r.label,
                "color": r.color,
                "caption": r.caption,
                "score": round(r.score, 4),
            }
            for r in results
        ]
    except Exception as exc:
        logger.error("run_search_tool failed: %s", exc)
        return []


def run_recommend_tool(
    style: str = "",
    occasion: str = "",
    gender: str = "",
    top_k: int = 3,
) -> list[dict]:
    """Execute a recommendation search for a style or occasion.

    Constructs a synthetic query and delegates to hybrid_search.

    Args:
        style: Target style (e.g. casual, formal, bohemian).
        occasion: Target occasion (e.g. office, wedding).
        gender: Optional gender filter.
        top_k: Max products per search.

    Returns:
        List of product dicts.
    """
    from search.search_engine import search as hybrid_search

    parts = []
    if occasion:
        parts.append(occasion)
    if style:
        parts.append(style)
    if not parts:
        parts = ["fashion outfit"]

    query = " ".join(parts) + " outfit"

    filters: dict[str, str] = {}
    if gender and gender not in ("", "unisex"):
        filters["gender"] = gender

    try:
        results = hybrid_search(query, top_k=top_k, use_query_expansion=False, filters=filters)
        return [
            {
                "image_id": r.image_id,
                "image_path": r.image_path,
                "label": r.label,
                "color": r.color,
                "caption": r.caption,
                "score": round(r.score, 4),
            }
            for r in results
        ]
    except Exception as exc:
        logger.error("run_recommend_tool failed: %s", exc)
        return []
