## ADDED Requirements

### Requirement: Completeness threshold for search activation
The system SHALL compute slot completeness and only proceed to search when ALL of the following are met:
- `category` slot is filled (non-null, non-empty)
- `color` slot is filled (non-null, non-empty)
- At least 3 out of 4 caption slots are filled (fabric, fit, construction, aesthetic)

#### Scenario: All slots filled → immediate search
- **WHEN** extracted slots are: category="Shirt", color="white", fabric="cotton", fit="slim fit", construction=null, aesthetic="formal"
- **THEN** system proceeds to search immediately (category ✅, color ✅, caption=3/4 ✅)

#### Scenario: Only category and color → ask more
- **WHEN** extracted slots are: category="Shirt", color="white", fabric=null, fit=null, construction=null, aesthetic=null
- **THEN** system SHALL NOT search and SHALL ask clarification about missing caption slots

#### Scenario: Missing category → ask for category
- **WHEN** extracted slots are: category=null, color="red", fabric="silk", fit="A-line", construction=null, aesthetic="elegant"
- **THEN** system SHALL NOT search and SHALL ask what type of clothing the user wants

### Requirement: Targeted clarification questions
When completeness threshold is not met, the system SHALL generate a clarification question that specifically asks about the MISSING slots. The question SHALL NOT be generic.

#### Scenario: Missing fabric and fit
- **WHEN** category="Dress", color="black", fabric=null, fit=null, construction=null, aesthetic=null
- **THEN** system asks specifically about chất liệu (fabric), dáng (fit), and phong cách (aesthetic)

#### Scenario: Missing only color
- **WHEN** category="Shirt", color=null, fabric="cotton", fit="slim fit", construction="collar", aesthetic=null
- **THEN** system asks specifically about màu sắc (color)

### Requirement: Maximum clarification turns
The system SHALL ask at most 3 clarification turns. After 3 turns, the system SHALL proceed to search with whatever slots are available.

#### Scenario: Exceed max turns
- **WHEN** user has been asked 3 clarification questions and still has insufficient slots
- **THEN** system proceeds to search with the best available information

### Requirement: Slot-based completeness only for text_search intent
The slot completeness check SHALL only apply when `intent == "text_search"`. Other intents (outfit_request, follow_up, out_of_scope) SHALL use existing flow.

#### Scenario: Outfit request bypasses slot check
- **WHEN** intent is "outfit_request"
- **THEN** system proceeds without slot completeness check
