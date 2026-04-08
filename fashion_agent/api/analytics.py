"""
Thesis evaluation analytics endpoints.

Three evaluation axes (token costs, behavioural accuracy, gender‑AB) are
exposed as admin-only GET endpoints.  All data is pulled from the same
PostgreSQL database that the fashion agent already uses.

Pricing constants are hardcoded so the thesis numbers are reproducible.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from fastapi import HTTPException, Request

# ── LLM pricing: USD per 1 M tokens (early‑2025 list prices) ─────────────
PRICING: dict[str, dict[str, float]] = {
    # Gemini 2.0 Flash
    "gemini": {"input": 0.075, "output": 0.30},
    # GPT-4o
    "gpt":    {"input": 2.50,  "output": 10.00},
    # Claude 3.5 Sonnet
    "claude": {"input": 3.00,  "output": 15.00},
}

# ── Categories used for gender inference (fashion_items has no gender col) ─
MALE_CATEGORIES = frozenset({
    "Longsleeve", "T-Shirt", "Shirt", "Hoodie", "Shorts",
    "Pants", "Blazer", "Polo",
})
FEMALE_CATEGORIES = frozenset({
    "Dress", "Skirt", "Blouse", "Top",
})
# Everything else is considered "unisex" and excluded from GAS.


def _db_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "fashion_rag"),
        user=os.getenv("PGUSER", "fashion_user"),
        password=os.getenv("PGPASSWORD", ""),
        connect_timeout=5,
    )


def _require_admin(request: Request) -> None:
    """Verify X-Admin-Key header. Raises 403/503 on failure."""
    admin_key = os.getenv("ADMIN_SECRET_KEY", "")
    if not admin_key:
        raise HTTPException(
            status_code=503,
            detail="Analytics not configured (ADMIN_SECRET_KEY missing)",
        )
    if request.headers.get("X-Admin-Key", "") != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")


# ═══════════════════════════════════════════════════════════════════════════
# 1. GET /api/analytics/token-costs
# ═══════════════════════════════════════════════════════════════════════════

async def get_token_costs(request: Request) -> dict[str, Any]:
    """Token cost breakdown by orchestration mode.

    Returns data from the ``mode_cost_summary`` view (created in
    ``init_memory_tables``).  Each row has session/turn counts, average
    token usage, and estimated per-turn USD cost.

    Protected by ``X-Admin-Key``.
    """
    _require_admin(request)

    try:
        conn = _db_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM mode_cost_summary ORDER BY orchestration_mode;")
            rows = [dict(r) for r in cur.fetchall()]

            # Grand totals
            cur.execute("""
                SELECT
                    COUNT(DISTINCT session_id) AS total_sessions,
                    COUNT(*)                   AS total_turns,
                    SUM(input_tokens + output_tokens
                        + orchestrator_input_tokens + orchestrator_output_tokens) AS total_tokens
                FROM llm_token_usage
                WHERE call_name = 'synthesis';
            """)
            totals = dict(cur.fetchone() or {})
        conn.close()

        # Serialise Decimal → float
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "as_tuple"):  # Decimal
                    row[k] = float(v)

        for k, v in totals.items():
            if v is not None and hasattr(v, "as_tuple"):
                totals[k] = float(v)

        return {
            "modes": rows,
            "totals": totals,
            "pricing_per_1m_tokens": PRICING,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════
# 2. GET /api/analytics/accuracy
# ═══════════════════════════════════════════════════════════════════════════

async def get_accuracy(request: Request) -> dict[str, Any]:
    """Behavioural accuracy metrics grouped by orchestration_mode.

    Computes:
      SR   – Selection Rate     = selected / impressions
      SCR  – Selection-to-Cart  = cart_add / selected
      QRR  – Query Refinement   = sessions with ≥2 queries / total sessions
      Converted                 = sessions that placed an order

    Uses ``session_token_summary`` to join preferred_model → orchestration_mode.

    Protected by ``X-Admin-Key``.
    """
    _require_admin(request)

    try:
        conn = _db_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH
                session_modes AS (
                    SELECT
                        s.session_id,
                        s.preferred_model,
                        COALESCE(st.orchestration_mode, 'unknown') AS orchestration_mode,
                        s.gender_hint_enabled
                    FROM user_sessions s
                    LEFT JOIN session_token_summary st USING (session_id)
                ),
                metrics AS (
                    SELECT
                        sm.orchestration_mode,
                        sm.session_id,
                        (SELECT COUNT(*) FROM product_impressions pi
                            WHERE pi.session_id = sm.session_id)          AS impressions,
                        (SELECT COUNT(*) FROM product_clicks pc
                            WHERE pc.session_id = sm.session_id)          AS clicks,
                        (SELECT COUNT(*) FROM selected_items si
                            WHERE si.session_id = sm.session_id)          AS selections,
                        (SELECT COUNT(*) FROM product_intents pit
                            WHERE pit.session_id = sm.session_id
                              AND pit.intent_type = 'will_buy')           AS will_buy,
                        (SELECT COUNT(*) FROM product_intents pit2
                            WHERE pit2.session_id = sm.session_id
                              AND pit2.intent_type = 'not_for_me')        AS not_for_me,
                        (SELECT COUNT(*) FROM user_orders uo
                            WHERE uo.session_id = sm.session_id)          AS orders,
                        (SELECT COUNT(DISTINCT search_query)
                            FROM product_impressions pi3
                            WHERE pi3.session_id = sm.session_id
                              AND pi3.search_query <> '')                 AS distinct_queries
                    FROM session_modes sm
                )
                SELECT
                    orchestration_mode,
                    COUNT(*)                                                AS n_sessions,
                    SUM(impressions)                                         AS total_impressions,
                    SUM(clicks)                                             AS total_clicks,
                    SUM(selections)                                         AS total_selections,
                    SUM(will_buy)                                           AS total_will_buy,
                    SUM(not_for_me)                                         AS total_not_for_me,
                    SUM(orders)                                             AS total_orders,
                    ROUND(SUM(selections)::numeric
                        / NULLIF(SUM(impressions), 0), 4)                   AS sr,
                    ROUND(SUM(will_buy)::numeric
                        / NULLIF(SUM(selections), 0), 4)                    AS scr,
                    ROUND(SUM(CASE WHEN distinct_queries >= 2 THEN 1 ELSE 0 END)::numeric
                        / NULLIF(COUNT(*), 0), 4)                           AS qrr,
                    ROUND(SUM(orders)::numeric
                        / NULLIF(COUNT(*), 0), 4)                           AS conversion_rate
                FROM metrics
                GROUP BY orchestration_mode
                ORDER BY orchestration_mode;
            """)
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        # Decimal → float
        for row in rows:
            for k, v in row.items():
                if v is not None and hasattr(v, "as_tuple"):
                    row[k] = float(v)

        return {"modes": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════
# 3. GET /api/analytics/gender-ab
# ═══════════════════════════════════════════════════════════════════════════

async def get_gender_ab(request: Request) -> dict[str, Any]:
    """Gender-Appropriate Selection (GAS) analysis.

    Uses category-based gender inference: if the user's self-reported
    ``gender`` is male and the selected item's label is in
    ``FEMALE_CATEGORIES``, it is a mismatch (and vice-versa).

    GAS = gender-match selections / total gender-applicable selections.

    Results are grouped by (gender_hint_enabled, orchestration_mode).

    Protected by ``X-Admin-Key``.
    """
    _require_admin(request)

    try:
        conn = _db_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH
                session_modes AS (
                    SELECT
                        s.session_id,
                        s.gender,
                        s.gender_hint_enabled,
                        COALESCE(st.orchestration_mode, 'unknown') AS orchestration_mode
                    FROM user_sessions s
                    LEFT JOIN session_token_summary st USING (session_id)
                    WHERE s.gender IS NOT NULL
                ),
                selection_gender AS (
                    SELECT
                        sm.session_id,
                        sm.gender,
                        sm.gender_hint_enabled,
                        sm.orchestration_mode,
                        si.label,
                        CASE
                            WHEN sm.gender = 'male'   AND si.label = ANY(%s) THEN 'match'
                            WHEN sm.gender = 'male'   AND si.label = ANY(%s) THEN 'mismatch'
                            WHEN sm.gender = 'female' AND si.label = ANY(%s) THEN 'match'
                            WHEN sm.gender = 'female' AND si.label = ANY(%s) THEN 'mismatch'
                            ELSE 'unisex'
                        END AS gender_match
                    FROM session_modes sm
                    JOIN selected_items si USING (session_id)
                )
                SELECT
                    gender_hint_enabled,
                    orchestration_mode,
                    COUNT(*)                                                    AS total_selections,
                    SUM(CASE WHEN gender_match <> 'unisex' THEN 1 ELSE 0 END)  AS gendered_selections,
                    SUM(CASE WHEN gender_match = 'match' THEN 1 ELSE 0 END)    AS matched,
                    SUM(CASE WHEN gender_match = 'mismatch' THEN 1 ELSE 0 END) AS mismatched,
                    ROUND(
                        SUM(CASE WHEN gender_match = 'match' THEN 1 ELSE 0 END)::numeric
                        / NULLIF(
                            SUM(CASE WHEN gender_match <> 'unisex' THEN 1 ELSE 0 END),
                            0
                        ), 4
                    )                                                           AS gas
                FROM selection_gender
                GROUP BY gender_hint_enabled, orchestration_mode
                ORDER BY gender_hint_enabled, orchestration_mode;
            """, (
                list(MALE_CATEGORIES),
                list(FEMALE_CATEGORIES),
                list(FEMALE_CATEGORIES),
                list(MALE_CATEGORIES),
            ))
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        # Decimal → float
        for row in rows:
            for k, v in row.items():
                if v is not None and hasattr(v, "as_tuple"):
                    row[k] = float(v)

        return {
            "groups": rows,
            "male_categories": sorted(MALE_CATEGORIES),
            "female_categories": sorted(FEMALE_CATEGORIES),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
