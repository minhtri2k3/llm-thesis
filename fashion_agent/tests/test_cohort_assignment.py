"""Integration tests for assign_cohort_session() — round-robin balance and exhaustion.

Uses an in-memory monkeypatch of `_db_conn()` so the tests can run without a
real Postgres. The fake mimics the SQL the real function issues.
"""

import pytest
import sys
import os
from contextlib import contextmanager
from collections import defaultdict
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Lightweight in-memory fake of the slice of postgres assign_cohort_session uses
# ---------------------------------------------------------------------------

class _FakeDB:
    """Stores user_sessions rows: (user_name, study_group, agent_codename)."""

    def __init__(self):
        # list of dicts simulating user_sessions rows
        self.rows: list[dict] = []

    def insert(self, user_name: str, group: str | None, codename: str | None):
        self.rows.append({
            "user_name": user_name,
            "study_group": group,
            "agent_codename": codename,
        })

    def execute(self, sql: str, params=()):
        sql_norm = " ".join(sql.split())
        if "GROUP BY study_group" in sql_norm:
            user_name = params[0]
            counts = defaultdict(int)
            for r in self.rows:
                if r["user_name"] == user_name and r["study_group"] is not None:
                    counts[r["study_group"]] += 1
            self._fetch = [{"study_group": g, "n_sessions": n} for g, n in counts.items()]
        elif "COUNT(DISTINCT user_name)" in sql_norm:
            distinct = {r["user_name"] for r in self.rows if r["study_group"] is not None}
            self._fetch = [(len(distinct),)]
        else:
            self._fetch = []

    def fetchall(self):
        return self._fetch

    def fetchone(self):
        return self._fetch[0] if self._fetch else None


class _FakeCursor:
    def __init__(self, db: _FakeDB):
        self._db = db

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        self._db.execute(sql, params)

    def fetchall(self):
        return self._db.fetchall()

    def fetchone(self):
        return self._db.fetchone()


class _FakeConn:
    def __init__(self, db: _FakeDB):
        self._db = db

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self, cursor_factory=None):
        return _FakeCursor(self._db)

    def commit(self):
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_db():
    db = _FakeDB()

    @contextmanager
    def _conn_ctx():
        yield _FakeConn(db)

    with patch("agent.memory._db_conn", _conn_ctx):
        yield db


def test_first_user_assigned_group1_indigo(fake_db):
    from agent.memory import assign_cohort_session
    group, codename, model_id, idx = assign_cohort_session("alice")
    assert group == "Group1"
    assert codename == "Indigo"
    assert model_id == "gemini-2.5-flash"
    assert idx == 0


def test_round_robin_across_four_users(fake_db):
    from agent.memory import assign_cohort_session
    seen = []
    for name in ["alice", "bob", "carol", "dan"]:
        g, c, m, i = assign_cohort_session(name)
        # Persist each assignment as a row so subsequent calls see it.
        fake_db.insert(name, g, c)
        seen.append(g)
    assert seen == ["Group1", "Group2", "Group3", "Group4"]


def test_returning_user_advances_session_index(fake_db):
    from agent.memory import assign_cohort_session
    g, c, m, i = assign_cohort_session("alice")
    fake_db.insert("alice", g, c)
    g2, c2, m2, i2 = assign_cohort_session("alice")
    fake_db.insert("alice", g2, c2)
    assert g == g2 == "Group1"
    assert i == 0
    assert i2 == 1
    assert c == "Indigo"
    assert c2 == "Crimson"  # session 2 in Group1's row


def test_full_run_through_all_four_sessions(fake_db):
    from agent.memory import assign_cohort_session
    codenames = []
    for _ in range(4):
        g, c, m, i = assign_cohort_session("alice")
        fake_db.insert("alice", g, c)
        codenames.append(c)
    assert codenames == ["Indigo", "Crimson", "Emerald", "Amber"]


def test_fifth_session_raises_exhausted(fake_db):
    from agent.memory import assign_cohort_session
    from agent.cohort import CohortStudyExhausted
    for _ in range(4):
        g, c, m, i = assign_cohort_session("alice")
        fake_db.insert("alice", g, c)
    with pytest.raises(CohortStudyExhausted):
        assign_cohort_session("alice")


def test_unreachable_codename_skipped(fake_db):
    from agent.memory import assign_cohort_session
    # Group 1's session 0 is Indigo. If Indigo is unreachable, skip to Crimson.
    g, c, m, i = assign_cohort_session("alice", unreachable_codenames={"Indigo"})
    assert c == "Crimson"
    assert i == 1


def test_all_unreachable_raises_exhausted(fake_db):
    from agent.memory import assign_cohort_session
    from agent.cohort import CohortStudyExhausted
    with pytest.raises(CohortStudyExhausted):
        assign_cohort_session(
            "alice",
            unreachable_codenames={"Indigo", "Crimson", "Emerald", "Amber"},
        )


def test_empty_user_name_raises():
    from agent.memory import assign_cohort_session
    with pytest.raises(ValueError):
        assign_cohort_session("")
