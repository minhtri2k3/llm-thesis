# Design: Order Rating Flow

## Context

The Clothie web frontend (Flutter Web) has a `CartScreen` → order dialog flow that currently ends with a SnackBar notification. A `RatingDialog` already exists and is used by the "End Session" button in `ChatScreen`. The `RatingScreen` (full-page) and `RatingDialog` (modal) both navigate to `SplashScreen` after submission.

Current navigation: `ChatScreen` → `CartScreen.show()` → `_showOrderDialog()` → SnackBar → done.

## Goals / Non-Goals

**Goals:**
- After successful order placement, automatically show the `RatingDialog` to collect user feedback
- After rating submission, navigate to `RegisterScreen` (not `SplashScreen`) so the next participant can start a fresh session
- Keep changes minimal — reuse existing `RatingDialog` component

**Non-Goals:**
- Changing the RatingDialog UI itself
- Adding new API endpoints — all backend endpoints already exist
- Modifying the order API response

## Decisions

### 1. CartScreen returns a result via `Navigator.pop(context, true)`

**Decision**: Use a boolean return value from `CartScreen.show()` to signal "order placed" back to `ChatScreen`.

**Alternatives considered**:
- *Callback parameter*: Pass an `onOrderPlaced` callback — adds coupling between CartScreen and the rating flow.
- *Show RatingDialog from inside CartScreen*: CartScreen is a modal bottom sheet and shouldn't own full-app navigation.

**Rationale**: Returning a value keeps CartScreen focused on its single responsibility (cart management) and lets ChatScreen orchestrate the navigation flow.

### 2. ChatScreen orchestrates the rating popup

**Decision**: `ChatScreen` awaits the `CartScreen.show()` Future. If it returns `true`, ChatScreen calls `_showRatingDialog()`.

**Rationale**: ChatScreen already owns the "End Session" → rating flow. Adding the post-order trigger here keeps all rating orchestration in one place.

### 3. Navigate to `/register` instead of SplashScreen

**Decision**: Change both `RatingDialog.onComplete` (in ChatScreen) and `RatingScreen._submit()` to navigate to `RegisterScreen` via `context.goNamed('register')`.

**Rationale**: SplashScreen is a brief intro animation — skipping it and going directly to register provides a faster turnaround for the next thesis participant.

## Risks / Trade-offs

- **[Minor] User can dismiss RatingDialog**: The "Maybe later" button in `RatingDialog` lets users skip rating. This is acceptable — forced rating would create low-quality data. → No mitigation needed, existing behavior is intentional.
- **[Minor] CartScreen needs `userName`**: Currently CartScreen only accepts `sessionId`. We need to add `userName` so it can be passed to `RatingDialog` if shown from CartScreen context. → Add `userName` parameter to `CartScreen` and its `.show()` method.
