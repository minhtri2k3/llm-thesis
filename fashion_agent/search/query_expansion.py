"""
Gemini-powered query expansion for fashion search.

Generates synonym/variation queries to improve recall in hybrid search.
Ported from notebook research (RAG_clothes_FashionCLIP2.ipynb Cell 28).
"""

from __future__ import annotations

import json
import re

from shared.llm import get_model
from agent.prompts import EXPANSION_PROMPT


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_EXPANSIONS = 3
SHORT_QUERY_THRESHOLD = 6  # Only expand queries with fewer than this many words


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def expand_query(
    query: str,
    max_expansions: int = MAX_EXPANSIONS,
) -> list[str]:
    """
    Expand a search query into synonym/variation queries using Gemini.

    Args:
        query:            Original user search query.
        max_expansions:   Maximum number of expanded queries (including original).

    Returns:
        List of expanded queries. Always includes the original query.
        On failure, returns [query] (original only).
    """
    # Short-query gate: skip expansion for long/complex queries
    word_count = len(query.strip().split())
    if word_count >= SHORT_QUERY_THRESHOLD:
        return [query]

    try:
        model = get_model()

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
