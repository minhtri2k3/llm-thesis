# Proposal: Order Rating Flow

## Why

After a user places an order in CartScreen, the session ends silently with only a SnackBar — no feedback is collected. This misses a critical data-collection opportunity for thesis evaluation. We need to prompt users to rate their experience immediately after order confirmation, then redirect them to the register screen so they (or the next participant) can start a fresh session.

## What Changes

- **CartScreen**: After a successful order, close the order dialog and the cart bottom sheet, then trigger a `RatingDialog` popup.
- **RatingDialog / RatingScreen**: After rating submission, navigate to `RegisterScreen` instead of `SplashScreen`.
- **ChatScreen**: Orchestrate the new flow — await `CartScreen.show()` result, show rating dialog on order completion, and route to `/register` on rating completion.
- **Docker**: Rebuild `clothie-web` container after code changes.

## Capabilities

### New Capabilities

- `post-order-rating`: Wire the order confirmation in CartScreen to trigger the RatingDialog popup, passing sessionId and userName. CartScreen returns a boolean result to signal that an order was placed.

### Modified Capabilities

_(none — no existing spec-level requirements are changing)_

## Impact

- `clothie_web/lib/screens/cart_screen.dart` — add `userName` param, return `true` after order, remove SnackBar
- `clothie_web/lib/screens/chat_screen.dart` — await cart result, show RatingDialog, change onComplete destination from `splash` → `register`
- `clothie_web/lib/screens/rating_screen.dart` — change standalone RatingScreen post-submit navigation from SplashScreen → RegisterScreen
- Docker: `docker compose build --no-cache clothie-web && docker compose up -d`
