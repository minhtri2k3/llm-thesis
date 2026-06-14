from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.intent_classifier import ClassifiedIntent, ExtractedSlots
from agent.utils import _find_category_suggestions, normalize_category


def test_exact_category_is_canonicalized_case_insensitively():
    result = normalize_category("pants")

    assert result.resolved
    assert result.category == "Pants"
    assert result.method == "exact"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("trousers", "Pants"),
        ("trouser", "Pants"),
        ("tee", "T-Shirt"),
        ("tshirt", "T-Shirt"),
        ("sneakers", "Shoes"),
    ],
)
def test_category_synonyms_resolve_to_canonical_labels(raw: str, expected: str):
    result = normalize_category(raw)

    assert result.resolved
    assert result.category == expected
    assert result.method in {"exact", "synonym"}


def test_category_typo_resolves_when_confident():
    result = normalize_category("panst")

    assert result.resolved
    assert result.category == "Pants"
    assert result.method == "fuzzy"


def test_unrelated_unsupported_category_does_not_resolve():
    result = normalize_category("bag")

    assert not result.resolved
    assert result.category == ""


def test_unsupported_suggestions_reuse_canonicalization():
    assert _find_category_suggestions("trousers") == ["Pants"]


def test_resolve_search_query_canonicalizes_trousers_filter():
    from agent import fashion_agent

    session_id = "category-canonicalization-test"
    fashion_agent._session_accumulated_slots.pop(session_id, None)
    fashion_agent._session_ranked_slots.pop(session_id, None)
    intent_result = ClassifiedIntent(
        intent="text_search",
        confidence=0.95,
        filters={"category": "trousers", "color": "black", "style": "", "occasion": ""},
        refined_query="black trousers",
        extracted_slots=ExtractedSlots(category="trousers", color="black"),
    )

    search_query, clarification, accumulated = fashion_agent._resolve_search_query(
        "text_search",
        intent_result,
        session_id,
        history=[],
        query="I need black trousers",
    )

    assert clarification == ""
    assert accumulated.category == "Pants"
    assert intent_result.filters["category"] == "Pants"
    assert "Pants" in search_query
    assert "trousers" in search_query


def test_category_list_query_bypasses_stale_invalid_slot():
    from agent import fashion_agent

    session_id = "category-list-stale-slot-test"
    fashion_agent._session_accumulated_slots[session_id] = ExtractedSlots(category="Trousers")
    fashion_agent._session_ranked_slots[session_id] = {"category": "Trousers"}

    assert fashion_agent._is_category_list_query("what categories do you have?")
    response = fashion_agent._build_category_list_response("what categories do you have?")

    assert "Pants" in response
    assert "T-Shirt" in response
