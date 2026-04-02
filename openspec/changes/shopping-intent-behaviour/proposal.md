 dta# Proposal: Shopping Intent & Behaviour Stress Test

## Summary

Transform the Clothie fashion agent from a simple "save item" demo into a **behavioural research instrument** that captures real purchase-intent signals — without requiring real money. This enables Precision@K evaluation against ground-truth intent rather than agent ratings.

## Problem

The current system has two gaps:

1. **UX friction**: When a user confirms an item, the agent responds with a terse `"💾 Saved 1 item(s)!"` and the cart banner says `"Item saved! ✨"`. These feel robotic and do not guide the user to their next action.

2. **Research instrumentation is incomplete**: The evaluation funnel stops at *Add to Cart*. There is no way to distinguish between items the user *added* from curiosity versus items they *genuinely intended to purchase*. Without this signal, Precision@K cannot be computed honestly.

## Proposed Solution

Four coordinated changes:

### 1 — Natural Language Cart Confirmation
Replace the mechanical confirmation message with language that mirrors how the agent is speaking to the user. The banner becomes: *"I added it to the cart for you — check the top‑right corner 🛍️"*.

### 2 — Order Flow (Phone + Address Capture)
Add a **"Let's make the order 📦"** CTA to `CartScreen`. Tapping it opens a lightweight form that collects phone number and delivery address. The order record is saved to a new `user_orders` table. This is simulated checkout — no payment gateway — but it produces a meaningful *order intent* signal for thesis data.

### 3 — Purchase Intent Buttons + Behaviour Database
Add two micro-interaction buttons to each item card inside `CartScreen`:

- **`✓ I'll buy this`** — stronger than "add to cart"; signals genuine purchase intent
- **`✗ Not for me`** — negative signal + optional qualitative reason

These feed a new `product_intents` table. Combined with the existing `selected_items` table and a new `product_impressions` table (auto-logged when search results arrive), the full funnel is captured:

```
Impression → Cart Add → Intent ("will_buy" | "not_for_me")
                                  ↓
                       Precision@K = will_buy / impressions
```

### 4 — Stress Test Structure
Frame the entire session as a controlled user study. The research claim becomes: *"The fashion agent's recommendations correlate with real purchase intent, as measured by the will_buy signal rate compared to a baseline random recommender."*

## Why This Approach

- **No real money required** — decouples evaluation from price sensitivity
- **Non-breaking** — all changes are additive; existing ratings and cart flow still work
- **Minimal UI surface** — intent buttons live in `CartScreen`, not in the noisy chat bubble
- **DB-backed** — all events are persisted and queryable via analytics API

## Out of Scope

- Real payment integration
- Tracking clicks on individual products in the chat bubble (would require significant chat rendering changes; deferred)
- Recommend algorithm changes based on intent signals (future work)

## Success Criteria

1. Banner text on cart-save is conversational, not robotic
2. User can place a simulated order (phone + address saved to DB)
3. Intent buttons (`✓` / `✗`) appear on items in `CartScreen` and write to `product_intents`
4. Impression events are auto-logged when `products` SSE fires
5. Analytics endpoint returns the full funnel (impressions / cart / will_buy / not_for_me)
6. Precision@K is computable from the resulting data
