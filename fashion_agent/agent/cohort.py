"""Cohort study constants and assignment helpers (4-Gemini A/B/C/D).

Single source of truth for the codename ↔ model mapping used by the
controlled study. Imported by both the API (assignment) and the
analytics endpoint (dashboard mapping). Tester-facing UI shows
codenames only; admin views resolve them via this module.
"""

from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# Codename ↔ Model mapping (FIXED for the duration of the study)
# ---------------------------------------------------------------------------

CODENAME_TO_MODEL: dict[str, str] = {
    "Indigo":  "gemini-2.5-flash",       # cheap tier, current generation (anchor)
    "Crimson": "gemini-2.5-pro",         # top tier, current generation
    "Emerald": "gemini-3.1-flash-lite",  # cheap tier, newer generation
    "Amber":   "gemini-3.1-pro-preview", # top tier, newer generation
}

MODEL_TO_CODENAME: dict[str, str] = {v: k for k, v in CODENAME_TO_MODEL.items()}

# Ordered list of codenames in their canonical 2x2 layout (Indigo, Crimson,
# Emerald, Amber). Used for round-robin smoke-testing and as the order of
# Group 1's session sequence in the Latin square below.
COHORT_CODENAMES: list[str] = ["Indigo", "Crimson", "Emerald", "Amber"]
COHORT_MODELS: list[str] = [CODENAME_TO_MODEL[c] for c in COHORT_CODENAMES]


# ---------------------------------------------------------------------------
# Latin square — group × session_index → codename
# ---------------------------------------------------------------------------
#
# 4 groups, 4 sessions each. Each codename appears exactly once in each
# session position across the 4 groups (counterbalances order effects).
#
#               Session 1   Session 2   Session 3   Session 4
#   Group1      Indigo      Crimson     Emerald     Amber
#   Group2      Crimson     Emerald     Amber       Indigo
#   Group3      Emerald     Amber       Indigo     Crimson
#   Group4      Amber       Indigo      Crimson     Emerald
LATIN_SQUARE: list[list[str]] = [
    ["Indigo",  "Crimson", "Emerald", "Amber"],   # Group1
    ["Crimson", "Emerald", "Amber",   "Indigo"],  # Group2
    ["Emerald", "Amber",   "Indigo",  "Crimson"], # Group3
    ["Amber",   "Indigo",  "Crimson", "Emerald"], # Group4
]

GROUP_NAMES: list[str] = ["Group1", "Group2", "Group3", "Group4"]
NUM_GROUPS: int = len(GROUP_NAMES)
SESSIONS_PER_USER: int = 4


class CohortStudyExhausted(Exception):
    """Raised when a tester has already completed all 4 cohort sessions."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assign_codename_for_session(group: str, session_index: int) -> str:
    """Return the codename for a (group, session_index) cell.

    Args:
        group: One of 'Group1' … 'Group4'.
        session_index: 0-based position in the user's session sequence (0..3).

    Raises:
        ValueError: if group is unknown or session_index is out of range.
    """
    if group not in GROUP_NAMES:
        raise ValueError(f"unknown group {group!r}; expected one of {GROUP_NAMES}")
    if not (0 <= session_index < SESSIONS_PER_USER):
        raise ValueError(
            f"session_index must be in [0, {SESSIONS_PER_USER}); got {session_index}"
        )
    row = GROUP_NAMES.index(group)
    return LATIN_SQUARE[row][session_index]


def codename_for_model(model_id: str) -> str | None:
    """Reverse-lookup: model ID → codename, or None if not in the cohort."""
    return MODEL_TO_CODENAME.get(model_id)


def model_for_codename(codename: str) -> str:
    """Forward-lookup: codename → model ID. Raises KeyError on unknown codename."""
    return CODENAME_TO_MODEL[codename]


def assign_group_round_robin(num_existing_users: int) -> str:
    """Assign a new tester to a group via round-robin on registration count."""
    return GROUP_NAMES[num_existing_users % NUM_GROUPS]


def filter_reachable(codenames: Iterable[str], unreachable: set[str]) -> list[str]:
    """Return the input codenames with unreachable ones filtered out (order preserved)."""
    return [c for c in codenames if c not in unreachable]
