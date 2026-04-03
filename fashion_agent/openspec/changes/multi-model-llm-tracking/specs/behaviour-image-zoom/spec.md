## ADDED Requirements

### Requirement: Fullscreen image overlay on card tap
When a user taps a product card image in `ProductCardList`, the system SHALL open a fullscreen dark overlay displaying the product image. The overlay SHALL support pinch-to-zoom and dismiss on tap outside or back gesture. The `logClick()` API call SHALL still fire on tap.

#### Scenario: Tap opens fullscreen
- **WHEN** user taps a product card image
- **THEN** a fullscreen dialog opens with the product image on a dark background, AND `logClick()` fires with the correct position

#### Scenario: Dismiss by tapping outside
- **WHEN** the fullscreen overlay is open and the user taps outside the image
- **THEN** the overlay closes and returns to the chat view

#### Scenario: Pinch to zoom
- **WHEN** the fullscreen overlay is open and the user pinches
- **THEN** the image scales smoothly using `InteractiveViewer`
