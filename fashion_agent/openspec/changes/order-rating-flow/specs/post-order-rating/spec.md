# Spec: Post-Order Rating

## ADDED Requirements

### Requirement: Rating popup after order confirmation

The system SHALL display the `RatingDialog` immediately after a user successfully places an order in `CartScreen`.

#### Scenario: Order placed successfully triggers rating popup

- **WHEN** the user fills in phone and address and confirms the order in the order dialog
- **AND** the `placeOrder` API call succeeds
- **THEN** the order dialog SHALL close
- **AND** the CartScreen bottom sheet SHALL close (returning `true` to the caller)
- **AND** the `RatingDialog` SHALL be displayed automatically

#### Scenario: Order fails — no rating popup

- **WHEN** the user confirms the order but the API call fails
- **THEN** an error message SHALL be shown
- **AND** the CartScreen bottom sheet SHALL remain open
- **AND** no `RatingDialog` SHALL appear

### Requirement: CartScreen accepts userName parameter

`CartScreen` and its static `show()` method SHALL accept a `userName` parameter in addition to `sessionId`, so that it can be forwarded when triggering the rating flow.

#### Scenario: CartScreen.show called with userName

- **WHEN** ChatScreen opens the cart via `CartScreen.show(context, sessionId, userName)`
- **THEN** the `userName` value SHALL be available for the RatingDialog invocation after order placement

### Requirement: Rating completion navigates to RegisterScreen

After successfully submitting a rating (via `RatingDialog` or `RatingScreen`), the system SHALL navigate to the `RegisterScreen` instead of `SplashScreen`.

#### Scenario: RatingDialog onComplete navigates to register

- **WHEN** the user submits a rating in the `RatingDialog` and the submission succeeds
- **THEN** the application SHALL navigate to `/register` route
- **AND** the previous navigation stack SHALL be cleared

#### Scenario: Standalone RatingScreen navigates to register

- **WHEN** a user submits a rating on the standalone `RatingScreen`
- **THEN** the application SHALL navigate to `RegisterScreen` via `pushAndRemoveUntil`
- **AND** the previous navigation stack SHALL be cleared
