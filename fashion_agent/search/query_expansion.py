"""
Gemini-powered query expansion for fashion search.

Generates synonym/variation queries to improve recall in hybrid search.
Ported from notebook research (RAG_clothes_FashionCLIP2.ipynb Cell 28).
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_EXPANSION_MODEL", "gemini-2.5-flash")
MAX_EXPANSIONS = 3
SHORT_QUERY_THRESHOLD = 6  # Only expand queries with fewer than this many words


# ---------------------------------------------------------------------------
# Expansion prompt (fashion-domain specific)
# ---------------------------------------------------------------------------

EXPANSION_PROMPT = """Generate {max_expansions} similar search queries for fashion items.
Each query should be a variation with synonyms or related terms.
Return ONLY a JSON array of strings, no explanation.

Original query: "{query}"

Example:
Original: "red dress"
Output: ["red dress", "crimson gown", "scarlet formal dress"]
"""


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def expand_query(
    query: str,
    max_expansions: int = MAX_EXPANSIONS,
    api_key: Optional[str] = None,
) -> list[str]:
    """
    Expand a search query into synonym/variation queries using Gemini.

    Args:
        query:            Original user search query.
        max_expansions:   Maximum number of expanded queries (including original).
        api_key:          Gemini API key (falls back to env var).

    Returns:
        List of expanded queries. Always includes the original query.
        On failure, returns [query] (original only).
    """
    # Short-query gate: skip expansion for long/complex queries
    word_count = len(query.strip().split())
    if word_count >= SHORT_QUERY_THRESHOLD:
        return [query]

    key = api_key or GEMINI_API_KEY
    if not key:
        print("[query_expansion] No GEMINI_API_KEY set, skipping expansion.")
        return [query]

    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = EXPANSION_PROMPT.format(
            max_expansions=max_expansions,
            query=query,
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Parse JSON array from response
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if not json_match:
            print(f"[query_expansion] No JSON array found in response: {text[:100]}")
            return [query]

        expanded = json.loads(json_match.group())

        # Ensure original query is included
        if query not in expanded:
            expanded.insert(0, query)

        result = expanded[:max_expansions]
        print(f"[query_expansion] '{query}' → {result}")
        return result

    except Exception as e:
        print(f"[query_expansion] Gemini expansion failed: {e}")
        return [query]
