# Proposal: Clothie Cart UX v2

## Summary

Three targeted fixes discovered after live testing the `clothie-ux-improvements` batch:

1. **Pre-confirm inline dialog** — "Add to Cart" currently skips straight to a backend text-based confirmation bubble. Replace with a lightweight FE-only inline dialog that shows the product preview before committing.
2. **Offer dialog with product mini-preview** — The `offer_prompt` dialog is a plain text AlertDialog. Upgrade it to include a horizontally-scrollable mini-grid of the products from that search so the user can see what they are deciding on.
3. **Always-on gender filter (remove A/B randomness)** — `gender_hint_enabled` is currently assigned 50/50 randomly per session, causing half of all male/female sessions to receive wrong-gender recommendations. Remove the coin flip; filter is always active when the user has provided a gender.

---

## Problem

### Problem 1: Add to Cart skips to text confirm step

Tapping "Add to Cart" (FAB in fullscreen or by text) immediately sends a number message to the backend. The backend responds with a `selection_confirm` SSE that renders as a chat bubble:

> "✅ You selected: 1. Shirt — Cream … Confirm? (yes/no)"

The user must then type "yes" to actually save the item. This creates friction — two confirmation steps — and the confirm bubble looks like a mid-conversation interruption rather than a natural cart interaction.

### Problem 2: Offer dialog shows no product context

The `offer_prompt` dialog reads: "Would you like to place an order for these items, or continue looking?" — but the user may have scrolled past the product images by the time the dialog appears and cannot recall which items they are being offered.

### Problem 3: Half of sessions ignore user's declared gender

`create_session()` calls `random.random() < 0.5` to set `gender_hint_enabled`. When it lands on `False`, `_filter_by_gender()` is skipped entirely — meaning a male user who explicitly selected "Male" during registration still receives dresses and skirts 50% of the time.

The A/B randomness was designed for controlled research, but it produces an inconsistent, broken demo experience. Historical A/B data already collected in the DB remains valid for thesis analysis; the change only affects new sessions going forward.

---

## Goals

- **Pre-confirm dialog**: Show a native FE dialog (product image + label + color) when user initiates cart add. Only send to backend after user confirms. The backend `selection_confirm → yes` roundtrip is preserved but invisible to the user — FE auto-sends "yes" silently and suppresses the confirm chat bubble.
- **Offer dialog upgrade**: Pass the current search's product list into the offer dialog. Render a horizontal thumbnail row above the action buttons so the user can see exactly what they are deciding on.
- **Always-on gender filter**: In `memory.py`, change the `gender_hint_enabled` assignment from a random coin flip to a deterministic rule: `True` if gender was provided by the user, `False` otherwise. No schema change, no analytics impact.

---

## Non-Goals

- Rebuilding the cart as a multi-item accumulation panel (future scope).
- Changing the backend `selection_confirm` SSE protocol.
- Modifying the gender A/B analytics endpoint `/api/analytics/gender-ab` (historical data stays).
- Any changes to rating, splash, or registration screens.
- Showing A/B group labels to users during the session.

---

## Scope

### Backend (`fashion_agent/`)

- `agent/memory.py`: Change `gender_hint_enabled = random.random() < 0.5` → `gender_hint_enabled = (gender is not None)` inside `create_session()`.

### Frontend (`clothie_web/`)

- `lib/widgets/product_card.dart`: FAB `onPressed` opens a pre-confirm `AlertDialog` instead of directly invoking `onCartTap`. On confirmation, sets `autoConfirmNext = true` on `ChatProvider` then calls `onCartTap`.
- `lib/providers/chat_provider.dart`: Add `bool autoConfirmNext = false` field. When `autoConfirmNext` is `true` and a `selection_confirm` SSE arrives, automatically fire `sendMessage("yes", sessionId)` and suppress the confirm bubble from rendering (set content to empty, clear confirmItems).
- `lib/screens/chat_screen.dart`: Pass `products` list from last message into `_showOfferDialog()`. Upgrade the dialog to a `Dialog` widget with a `SizedBox` product thumbnail row above the action buttons.

### Docker rebuild

- `docker compose build fashion-api` (memory.py change).
- `docker compose build clothie-web` (Flutter changes).
- `docker compose up -d`.

---

## Architecture Decisions

### Decision 1: FE pre-confirm with silent backend auto-confirm

Rather than adding a new backend intent/endpoint, the FE intercepts `selection_confirm` and auto-sends "yes". This reuses the entire existing `product_select → selection_confirm → selection_saved` pipeline with zero backend changes.

**Risk**: If the SSE stream drops after FE sends the item number but before it receives `selection_confirm`, `autoConfirmNext` may be left as `true`. **Mitigation**: Reset `autoConfirmNext` to `false` on any `done` or `error` SSE event, or after a 10-second timeout.

### Decision 2: Gender filter always-on when gender provided

`gender_hint_enabled = (gender is not None)` is semantically correct — there is no reason to disable gender filtering when the user has explicitly declared their gender. The DB column is preserved; analytics endpoints are unaffected. Historical sessions retain their original random assignment values for retrospective A/B analysis.

### Decision 3: Offer dialog gets products from last message

`provider.messages.last.products` is available in `ChatScreen` at the time `_showOfferDialog` is called (the `offer_prompt` SSE fires after `products` SSE). No extra state needed — pass the list as a parameter to `_showOfferDialog`.

---

## Success Criteria

- [ ] Tapping "Add to Cart" FAB opens a pre-confirm dialog with the product image, label, and color.
- [ ] Confirming in the dialog saves the item and shows the top banner — no text-based confirm bubble visible in chat.
- [ ] Cancelling in the dialog does nothing; user stays on the product grid.
- [ ] Male user searching for "shirt" receives 0 dresses/skirts in ALL sessions (not just 50%).
- [ ] Female user searching for "shirt" receives 0 men's hoodies/blazers in ALL sessions.
- [ ] The offer dialog shows a horizontal row of product thumbnails from the search.
- [ ] "Order now" in the offer dialog opens the cart screen.
- [ ] "Keep browsing" sends the decline sentinel; agent re-asks without showing another offer dialog.
- [ ] Docker stack rebuilds and starts cleanly after all changes.
