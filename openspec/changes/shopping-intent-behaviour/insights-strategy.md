# Insights Strategy: Proving the Fashion Agent Works

> **Session captured:** 2026-03-31  
> **Context:** Behavioural stress test design for Clothie thesis evaluation

---

## Core Principle

Instead of subjective ratings (1–10), we measure **real behavioural signals** that correlate with purchase intent — without requiring real money or a live e-commerce backend.

The chain is:

```
Impression → Click → Add to Cart → "Tôi sẽ mua" → (Order placed)
     ↓           ↓          ↓              ↓               ↓
  shown       tò mò     muốn giữ      sẽ mua thật    CR confirmed
```

Each step is a stronger signal than the one before. The agent's job is to surface items that reach the final steps.

---

## Data Sources (DB Tables)

| Table | Tracks | Added by |
|---|---|---|
| `product_impressions` | Every product shown in search results | Auto-logged on `products` SSE |
| `product_clicks` | User tapped a product card (1–6) | Flutter `GestureDetector.onTap` |
| `selected_items` | User added to cart | Existing flow |
| `product_intents` | ✓ `will_buy` / ✗ `not_for_me` | Intent buttons in CartScreen |
| `user_orders` | User placed simulated order (phone + address) | "Let's make the order" form |
| `llm_token_usage` | Tokens per call, per model | Already tracked per agent call |
| `user_sessions` | Demographics + session end time | Registration + order trigger |

---

## Funnel Metrics

```
CTR          = product_clicks     / product_impressions   (agent relevance at first glance)
Cart Rate    = selected_items     / product_clicks         (deeper engagement)
Intent Rate  = will_buy intents   / selected_items         (purchase seriousness)
CR           = sessions_with_order / total_sessions        (conversion — strongest signal)
Precision@K  = will_buy           / impressions            (overall recommendation quality)
```

---

## Claims → Metrics → Charts

| Thesis Claim | Metric | Chart Type | SQL Source |
|---|---|---|---|
| Agent surfaces relevant items | Precision@K per session | Bar chart (sessions on X-axis) | `product_intents` ÷ `product_impressions` |
| Users engage with recommendations | CTR = clicks / impressions | Funnel chart | `product_clicks` ÷ `product_impressions` |
| Agent works across demographics | CR by gender | Grouped bar (Male / Female) | `user_orders JOIN user_sessions` |
| Claude outperforms Gemini / GPT | CR and P@K by model | Comparison bar chart | `session_token_summary VIEW` |
| Token cost is justified | Tokens vs CR | Scatter plot | `session_token_summary` + `user_orders` |
| Older users have different intent | Age group × Intent Rate | Heatmap | `user_sessions.year_of_birth` bucketed |

---

## Model Comparison Table (template)

This is the central thesis contribution — no other fashion agent paper does this:

```
Model      │ Sessions │ Orders │   CR   │  P@K  │ Avg Tokens │ Efficiency (CR/token)
───────────┼──────────┼────────┼────────┼───────┼────────────┼──────────────────────
Claude     │    20    │   8    │  40%   │ 0.35  │   8,500    │   4.7 × 10⁻⁵
Gemini     │    20    │   6    │  30%   │ 0.28  │   6,200    │   4.8 × 10⁻⁵
GPT-4o     │    20    │   5    │  25%   │ 0.22  │   7,800    │   3.2 × 10⁻⁵
```

**Research question answered:** *"Which LLM backend provides the most accurate fashion recommendations, measured by real behavioural conversion, and at what token cost?"*

---

## SQL for Model Comparison (ready to run)

This SQL is already possible from existing tables:

```sql
SELECT
    sts.model_name,
    COUNT(DISTINCT sts.session_id)          AS sessions,
    COUNT(DISTINCT o.id)                    AS orders,
    ROUND(
        COUNT(DISTINCT o.id)::numeric /
        NULLIF(COUNT(DISTINCT sts.session_id), 0), 3
    )                                        AS conversion_rate,
    ROUND(AVG(sts.total_tokens))             AS avg_tokens
FROM session_token_summary sts
LEFT JOIN user_orders o USING (session_id)
GROUP BY sts.model_name
ORDER BY conversion_rate DESC;
```

---

## SQL for Full Funnel (per session aggregate)

```sql
SELECT
    s.session_id,
    s.user_name,
    s.gender,
    DATE_PART('year', NOW()) - s.year_of_birth   AS age,
    sts.model_name,
    sts.total_tokens,
    COUNT(DISTINCT pi.id)                         AS impressions,
    COUNT(DISTINCT pc.id)                         AS clicks,
    COUNT(DISTINCT si.id)                         AS cart_adds,
    COUNT(DISTINCT pit.id) FILTER
        (WHERE pit.intent_type = 'will_buy')       AS will_buy,
    COUNT(DISTINCT pit.id) FILTER
        (WHERE pit.intent_type = 'not_for_me')     AS not_for_me,
    CASE WHEN COUNT(DISTINCT o.id) > 0
         THEN 1 ELSE 0 END                         AS converted,

    -- Derived rates
    ROUND(COUNT(DISTINCT pc.id)::numeric /
          NULLIF(COUNT(DISTINCT pi.id), 0), 3)     AS ctr,
    ROUND(COUNT(DISTINCT si.id)::numeric /
          NULLIF(COUNT(DISTINCT pc.id), 0), 3)     AS cart_rate,
    ROUND(COUNT(DISTINCT pit.id) FILTER
          (WHERE pit.intent_type = 'will_buy')::numeric /
          NULLIF(COUNT(DISTINCT si.id), 0), 3)     AS intent_rate,
    ROUND(COUNT(DISTINCT pit.id) FILTER
          (WHERE pit.intent_type = 'will_buy')::numeric /
          NULLIF(COUNT(DISTINCT pi.id), 0), 3)     AS precision_at_k

FROM user_sessions s
LEFT JOIN product_impressions  pi  USING (session_id)
LEFT JOIN product_clicks       pc  USING (session_id)
LEFT JOIN selected_items       si  USING (session_id)
LEFT JOIN product_intents      pit USING (session_id)
LEFT JOIN user_orders           o  USING (session_id)
LEFT JOIN session_token_summary sts USING (session_id)
GROUP BY s.session_id, s.user_name, s.gender, s.year_of_birth,
         sts.model_name, sts.total_tokens
ORDER BY s.created_at DESC;
```

---

## Demographic Cross-Analysis

```sql
-- CR by gender
SELECT gender,
       COUNT(DISTINCT s.session_id)   AS sessions,
       COUNT(DISTINCT o.id)           AS orders,
       ROUND(COUNT(DISTINCT o.id)::numeric /
             NULLIF(COUNT(DISTINCT s.session_id), 0), 3) AS cr
FROM user_sessions s
LEFT JOIN user_orders o USING (session_id)
WHERE gender IS NOT NULL
GROUP BY gender;

-- Intent Rate by age group
SELECT
    CASE
        WHEN year_of_birth IS NULL        THEN 'unknown'
        WHEN year_of_birth >= 2005        THEN 'Gen Z (<21)'
        WHEN year_of_birth BETWEEN 1990 AND 2004 THEN 'Millennial (21-35)'
        WHEN year_of_birth BETWEEN 1975 AND 1989 THEN 'Gen X (36-50)'
        ELSE 'Boomer (50+)'
    END AS age_group,
    COUNT(DISTINCT pit.session_id) FILTER
        (WHERE pit.intent_type = 'will_buy')   AS will_buy_sessions,
    COUNT(DISTINCT s.session_id)               AS total_sessions,
    ROUND(
        COUNT(DISTINCT pit.session_id) FILTER
            (WHERE pit.intent_type = 'will_buy')::numeric /
        NULLIF(COUNT(DISTINCT s.session_id), 0), 3
    ) AS intent_rate
FROM user_sessions s
LEFT JOIN product_intents pit USING (session_id)
GROUP BY age_group
ORDER BY intent_rate DESC;
```

---

## Session End Flow

When a user places an order → session is considered **converted and complete**:

```
POST /api/sessions/{id}/orders
    ├── saves user_orders row
    └── sets user_sessions.ended_at = NOW()
              user_sessions.ended_by = 'order'

Session duration = ended_at - created_at
```

This means we can also measure: **how long does it take a user to convert?** Shorter = better agent UX.

---

## Implementation Order (BE → FE)

### Python (Backend) — do this first

1. `memory.py` — Add `product_clicks` table
2. `memory.py` — Add `ended_at`, `ended_by` to `user_sessions`
3. `memory.py` — Helper functions: `log_click()`, `end_session()`
4. `memory.py` — Helper: `get_model_comparison_stats()`
5. `main.py` — `POST /api/sessions/{id}/clicks`
6. `main.py` — `POST /api/sessions/{id}/impressions`
7. `main.py` — `POST /api/sessions/{id}/intents`
8. `main.py` — `POST /api/sessions/{id}/orders` (also ends session)
9. `main.py` — `GET /api/analytics/behaviour-funnel`

### Flutter (Frontend) — only after BE is done

10. `api_service.dart` — `logClick()`, `logImpression()`, `logIntent()`, `placeOrder()`
11. `chat_provider.dart` — auto-log impressions on `products` SSE event
12. Product card — `GestureDetector.onTap` → `logClick(imageId, position)`
13. `chat_screen.dart` — update cart banner text
14. `cart_screen.dart` — intent buttons ✓/✗ per card
15. `cart_screen.dart` — "Let's make the order" CTA + dialog

---

## Open Questions

- [ ] Will the study collect ≥20 sessions per model to reach statistical significance?
- [ ] How do we control for search query difficulty across model runs?
- [ ] "Click" definition confirmed: tap on product card in chat = click event
- [ ] Intent buttons location confirmed: CartScreen (not in chat bubble)
- [ ] "Not for me" → optional qualitative reason text field (skippable)
