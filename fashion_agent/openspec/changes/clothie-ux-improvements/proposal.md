# Proposal: Clothie UX Improvements

## Summary

A batch of 5 targeted improvements across the Fashion Agent backend (`fashion_agent/`) and the Clothie Flutter frontend (`clothie_web/`): gender-aware search filtering, dark-mode palette refinement, a quick-add-to-cart button inside the fullscreen image viewer, a post-suggestion "offer or keep browsing?" flow (trilingual EN/VN/ES), and an updated CTA prompt to match the new cart-focused UX.

## Problem

Several small but compounding UX gaps have been identified after user testing:

1. **Gender filter broken** — a male user receives female skirts because gender is stored per-session but never applied as a filter against product labels at search time. The products returned are semantically relevant but not gender-appropriate.
2. **Dark mode too dark** — the current `0xFF0C0C0C` background and `0xFF161616` card surface are nearly pure black, making text and card boundaries hard to read at normal screen brightness.
3. **No quick-add in image viewer** — users who open the fullscreen image preview have no direct way to add an item to their cart; they must close the dialog and type a number message in the chat.
4. **No offer prompt after successful suggestion** — the agent currently stops after showing products and emitting a CTA. There is no structured moment to ask "would you like to order now or keep browsing?", missing a natural conversion opportunity.
5. **CTA wording mismatch** — "Type a number (1-N) to select your favorite!" describes a selection mechanism, not the cart-focused outcome the user actually wants.

## Goals

- **Gender filter**: Post-search label filter using the existing `MALE_CATEGORIES`/`FEMALE_CATEGORIES` sets already defined in `analytics.py`. No Qdrant index rebuild needed.
- **Dark mode palette**: Lift `darkBackground`, `darkCard`, `darkBotBubble` to mid-dark grey/indigo-grey tones; keep accent colours unchanged.
- **Fullscreen cart button**: Add a "🛒 Add to Cart" FAB on the left side of the fullscreen dialog. Tapping it sends the product number as a chat message to trigger the existing `product_select → selection_confirm → selection_saved` flow.
- **Offer flow**: After products are emitted and synthesized, the backend emits a new `offer_prompt` SSE event. FE shows a dialog: YES → opens existing `CartScreen`; NO → sends a decline message, agent acknowledges and re-asks.
- **CTA text**: Replace "Type a number…" with "Tell me which one you like. I will add them into the cart." (trilingual).

## Non-Goals

- Rebuilding the Qdrant vector index with gender metadata fields.
- Adding gender filters to the agentic (Mode B/C) path beyond the text hint already in the prompt.
- A new cart/order screen (use existing `CartScreen`).
- Any changes to the rating, registration, or splash screens.

## Scope

### Backend (`fashion_agent/`)
- `agent/fashion_agent.py`: add `_filter_by_gender()`, call it in `_route_and_execute()`; add `offer_prompt` SSE emission after synthesis; add `offer_decline` intent handler; update CTA strings (3 locations).
- `agent/prompts.py` / `agent/utils.py`: update `SUPPORTED_CATEGORIES` comment if needed.
- Docker: rebuild `fashion-api` image to apply backend changes.

### Frontend (`clothie_web/`)
- `lib/theme/app_colors.dart`: update 3 dark-mode colour constants.
- `lib/widgets/product_card.dart`: add cart FAB inside `_showFullscreenImage()` dialog; pass `onAddToCart` callback from `_ProductCardState`.
- `lib/providers/chat_provider.dart`: handle new `offer_prompt` SSE event; expose `pendingOfferPrompt` flag.
- `lib/screens/chat_screen.dart`: observe `pendingOfferPrompt` and show the offer dialog; wire YES/NO buttons.
- Docker: rebuild `clothie-web` image.

## Architecture Decision

**Post-search label filter** (not Qdrant payload filter) chosen for gender enforcement because:
- `fashion_items` has no gender column — the Kaggle dataset uses category labels only.
- `analytics.py` already defines the authoritative category-to-gender mapping (`MALE_CATEGORIES`, `FEMALE_CATEGORIES`).
- Reusing the same set ensures analytics and runtime behaviour are consistent.
- No index rebuild required; filter runs in Python in `O(n)` where `n ≤ 6` results.

**`offer_prompt` as a new SSE event type** (not a chat text message) because:
- The FE needs a structured signal to show a native dialog, not just render markdown.
- Mirrors the existing `selection_confirm` SSE pattern already used for the confirmation step.

## Success Criteria

- [ ] Male user searching for "shirt" gets 0 skirts/dresses in results when `gender_hint_enabled = True`.
- [ ] Dark mode background is visibly grey (not black) at normal screen brightness.
- [ ] Tapping the cart FAB in fullscreen view triggers the normal confirm → save flow.
- [ ] After showing products, a dialog appears asking the user to offer or keep browsing.
- [ ] "No" in the offer dialog causes the agent to acknowledge, explain, and re-ask.
- [ ] All new user-facing strings appear correctly in EN, VN, and ES.
- [ ] Docker images rebuild and the full stack starts with `docker compose up -d`.
