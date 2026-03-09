## ADDED Requirements

### Requirement: Accumulate slots across conversation turns
The system SHALL maintain an accumulated set of slots within a conversation flow. When user provides new information in a follow-up turn, the new slots SHALL be merged with previously accumulated slots.

#### Scenario: Progressive slot filling
- **WHEN** turn 1 extracts category="Shirt", color="white" AND turn 2 extracts fabric="cotton", fit="slim fit", aesthetic="formal"
- **THEN** accumulated slots after turn 2 are: category="Shirt", color="white", fabric="cotton", fit="slim fit", construction=null, aesthetic="formal"

#### Scenario: Slot override on new turn
- **WHEN** accumulated slots have color="white" AND user says "còn màu xanh thì sao?"
- **THEN** color slot is updated to "blue", all other slots are preserved from previous turns

### Requirement: Follow-up inherits previous slots
When intent is "follow_up", the system SHALL merge current turn's extracted slots with the previous turn's accumulated slots. Only explicitly new or changed slots SHALL override.

#### Scenario: Color change follow-up
- **WHEN** previous accumulated slots are: category="Shirt", color="white", fabric="cotton", fit="slim fit", aesthetic="formal"
- **AND** user says "còn màu xanh thì sao?" (intent=follow_up, extracted color="blue")
- **THEN** accumulated becomes: category="Shirt", color="blue", fabric="cotton", fit="slim fit", aesthetic="formal"
- **AND** system proceeds to search (5/6 slots filled ✅)

### Requirement: Slot reset on new search topic
When the user starts a completely new search topic (intent="text_search" with new category different from accumulated), the system SHALL reset all accumulated slots and start fresh.

#### Scenario: New topic resets slots
- **WHEN** accumulated slots have category="Shirt" from previous search
- **AND** user says "bây giờ tìm quần jeans" (new topic, category="Pants")
- **THEN** accumulated slots are reset: category="Pants", all other slots=null
- **AND** system asks clarification for missing slots

### Requirement: Accumulated slots stored in-memory per session
Accumulated slots SHALL be stored in the chat function's local state within the request lifecycle. They SHALL NOT require database schema changes.

#### Scenario: Slots persist within session
- **WHEN** a session has ongoing conversation
- **THEN** accumulated slots are available for all turns within that session
