"""Unit tests for the cohort module — Latin square correctness and helpers.

These tests are pure-Python (no DB, no network) so they run instantly.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.cohort import (
    CODENAME_TO_MODEL,
    MODEL_TO_CODENAME,
    COHORT_CODENAMES,
    COHORT_MODELS,
    LATIN_SQUARE,
    GROUP_NAMES,
    NUM_GROUPS,
    SESSIONS_PER_USER,
    assign_codename_for_session,
    codename_for_model,
    model_for_codename,
    assign_group_round_robin,
    filter_reachable,
)


class TestMapping:
    def test_four_codenames(self):
        assert set(CODENAME_TO_MODEL.keys()) == {"Indigo", "Crimson", "Emerald", "Amber"}

    def test_four_distinct_models(self):
        assert len(set(CODENAME_TO_MODEL.values())) == 4

    def test_models_are_gemini(self):
        for m in CODENAME_TO_MODEL.values():
            assert m.startswith("gemini-"), f"{m} should be a Gemini model"

    def test_reverse_mapping_consistent(self):
        for codename, model in CODENAME_TO_MODEL.items():
            assert MODEL_TO_CODENAME[model] == codename

    def test_codename_list_matches_dict(self):
        assert set(COHORT_CODENAMES) == set(CODENAME_TO_MODEL.keys())
        assert COHORT_MODELS == [CODENAME_TO_MODEL[c] for c in COHORT_CODENAMES]


class TestLatinSquare:
    def test_shape(self):
        assert len(LATIN_SQUARE) == NUM_GROUPS == 4
        for row in LATIN_SQUARE:
            assert len(row) == SESSIONS_PER_USER == 4

    def test_each_codename_appears_once_per_session_position(self):
        """Counter-balance check — each codename in each column exactly once."""
        for col in range(SESSIONS_PER_USER):
            column = [LATIN_SQUARE[row][col] for row in range(NUM_GROUPS)]
            assert sorted(column) == sorted(COHORT_CODENAMES), (
                f"column {col}: {column} should be a permutation of {COHORT_CODENAMES}"
            )

    def test_each_codename_appears_once_per_group(self):
        for row in LATIN_SQUARE:
            assert sorted(row) == sorted(COHORT_CODENAMES)


class TestAssignCodenameForSession:
    def test_group1_session0(self):
        assert assign_codename_for_session("Group1", 0) == "Indigo"

    def test_group3_session2(self):
        assert assign_codename_for_session("Group3", 2) == "Indigo"

    def test_group4_session3(self):
        assert assign_codename_for_session("Group4", 3) == "Emerald"

    def test_unknown_group_raises(self):
        with pytest.raises(ValueError):
            assign_codename_for_session("Group5", 0)

    def test_session_index_negative_raises(self):
        with pytest.raises(ValueError):
            assign_codename_for_session("Group1", -1)

    def test_session_index_4_raises(self):
        with pytest.raises(ValueError):
            assign_codename_for_session("Group1", 4)


class TestRoundRobin:
    def test_first_user_group1(self):
        assert assign_group_round_robin(0) == "Group1"

    def test_fourth_user_group4(self):
        assert assign_group_round_robin(3) == "Group4"

    def test_fifth_user_wraps_to_group1(self):
        assert assign_group_round_robin(4) == "Group1"

    def test_round_robin_distribution(self):
        # 16 users → 4 per group
        counts = {g: 0 for g in GROUP_NAMES}
        for i in range(16):
            counts[assign_group_round_robin(i)] += 1
        assert all(c == 4 for c in counts.values())


class TestLookups:
    def test_codename_for_model_known(self):
        assert codename_for_model("gemini-2.5-flash") == "Indigo"
        assert codename_for_model("gemini-3.1-pro-preview") == "Amber"

    def test_codename_for_model_unknown(self):
        assert codename_for_model("gpt-4o") is None

    def test_model_for_codename(self):
        assert model_for_codename("Emerald") == "gemini-3.1-flash-lite"

    def test_model_for_codename_unknown_raises(self):
        with pytest.raises(KeyError):
            model_for_codename("Periwinkle")


class TestFilterReachable:
    def test_no_unreachable(self):
        assert filter_reachable(COHORT_CODENAMES, set()) == COHORT_CODENAMES

    def test_drops_unreachable(self):
        assert filter_reachable(COHORT_CODENAMES, {"Amber"}) == [
            "Indigo", "Crimson", "Emerald"
        ]

    def test_preserves_order(self):
        assert filter_reachable(["Amber", "Indigo"], {"Indigo"}) == ["Amber"]
