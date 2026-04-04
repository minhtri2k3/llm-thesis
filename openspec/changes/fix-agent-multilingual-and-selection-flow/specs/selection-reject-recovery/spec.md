## ADDED Requirements

### Requirement: Reject re-displays cached product list
After a user rejects a pending product selection, the system SHALL re-display a compact numbered summary of the 6 most recently shown products so the user MAY immediately choose a different number without issuing a new search query. The re-display MUST be language-aware (Vietnamese or English).

#### Scenario: User rejects and wants a different item from same set
- **WHEN** user sends a `REJECT_KEYWORD` message while a pending selection exists
- **THEN** the agent confirms cancellation AND displays a compact list of the 6 cached items with their numbers, labels, and colors
- **THEN** the agent invites the user to pick a new number

#### Scenario: No cached results on reject
- **WHEN** user sends a `REJECT_KEYWORD` but `_session_last_results` is empty or expired
- **THEN** the agent cancels gracefully and says "please search again" (no product list shown)

#### Scenario: Reject re-display in Vietnamese
- **WHEN** the rejected query is Vietnamese
- **THEN** the re-display message and invitation to re-select are written in Vietnamese

---

### Requirement: Non-keyword free-text clears stale pending state
When a user is in a pending-selection state and sends a free-text message that is NOT a confirm or reject keyword (e.g., "show me other products"), the system SHALL clear the pending selection before routing to intent classification, preventing ghost pending state from intercepting future sessions.

#### Scenario: User says something non-keyword while pending
- **WHEN** `_session_pending_selection[session_id]` is set AND user message matches neither `CONFIRM_KEYWORDS` nor `REJECT_KEYWORDS`
- **THEN** `_session_pending_selection[session_id]` is cleared
- **THEN** execution falls through to normal intent classification with stale state removed

#### Scenario: Pending state cleared before new search
- **WHEN** a new search is triggered (intent is `text_search` or `follow_up`) while a pending selection exists
- **THEN** `_session_pending_selection[session_id]` is cleared before the new `_session_last_results` is written

---

### Requirement: Selection index validation message is language-aware
When the user specifies an invalid product index (e.g., "7" when only 6 results exist), the error message MUST be in the user's language.

#### Scenario: Invalid index in Vietnamese context
- **WHEN** selected number is out of range and user message is Vietnamese
- **THEN** error message is in Vietnamese (e.g., "❌ Số không hợp lệ! Vui lòng chọn từ 1 đến {max}.")

#### Scenario: Invalid index in English context
- **WHEN** selected number is out of range and user message is English
- **THEN** existing English error message is shown
