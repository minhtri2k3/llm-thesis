# Tasks: Order Rating Flow

## 1. CartScreen — add userName and return order result

- [ ] 1.1 Add `userName` parameter to `CartScreen` constructor and its static `show()` method
- [ ] 1.2 Update `_showOrderDialog` — after successful `placeOrder()` API call, close the order dialog, then close the bottom sheet returning `true` via `Navigator.pop(context, true)`
- [ ] 1.3 Remove the SnackBar "🎉 Order placed!" notification (replaced by rating flow)

## 2. ChatScreen — orchestrate post-order rating

- [ ] 2.1 Update `CartScreen.show()` call in ChatScreen to pass `widget.userName` as the new parameter
- [ ] 2.2 Await the `CartScreen.show()` Future result — if it returns `true`, call `_showRatingDialog(context)`
- [ ] 2.3 Change `_showRatingDialog` `onComplete` callback from `context.goNamed('splash')` to `context.goNamed('register')`

## 3. RatingScreen — navigate to RegisterScreen

- [ ] 3.1 In `RatingScreen._submit()`, change the `pushAndRemoveUntil` destination from `SplashScreen` to `RegisterScreen` (update import accordingly)

## 4. Docker rebuild

- [ ] 4.1 Rebuild the `clothie-web` container: `docker compose build --no-cache clothie-web && docker compose up -d`
