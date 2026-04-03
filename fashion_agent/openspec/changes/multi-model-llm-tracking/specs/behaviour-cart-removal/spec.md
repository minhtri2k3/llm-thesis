## ADDED Requirements

### Requirement: Cart removal tracked in database
The system SHALL maintain a `cart_removals(id, session_id, image_id, removed_at)` table. When an item is removed from the cart, a row SHALL be inserted and the item SHALL be deleted from `selected_items`.

#### Scenario: Remove event recorded
- **WHEN** `DELETE /api/sessions/{id}/selections/{image_id}` is called
- **THEN** `selected_items` row for `(session_id, image_id)` is deleted AND a row is inserted into `cart_removals`

#### Scenario: Remove non-existent item returns 404
- **WHEN** the image_id does not exist in `selected_items` for the session
- **THEN** the API returns HTTP 404

### Requirement: Cart removal UI in _CartCard
Each cart card SHALL display a remove button (swipe-to-delete or explicit ❌ icon button). Tapping it SHALL call `ApiService.removeCartItem(sessionId, imageId)` and reload the cart.

#### Scenario: Remove button triggers API call
- **WHEN** user taps the remove button on a cart card
- **THEN** `DELETE /api/sessions/{id}/selections/{imageId}` is called and the card disappears from the cart

#### Scenario: Cart count updates after removal
- **WHEN** an item is successfully removed
- **THEN** the cart item count badge in the app bar decrements by 1
