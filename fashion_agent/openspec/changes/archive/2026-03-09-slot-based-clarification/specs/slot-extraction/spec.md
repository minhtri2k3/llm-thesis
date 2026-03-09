## ADDED Requirements

### Requirement: Extract 6 information slots from user query
The system SHALL extract 6 structured slots from the user's natural language query using LLM:
- `category`: Loại trang phục (e.g., "Shirt", "Dress", "Pants")
- `color`: Màu sắc (e.g., "white", "navy blue", "red with stripes")
- `fabric`: Chất liệu/texture (e.g., "cotton", "silk", "denim", "chiffon")
- `fit`: Dáng/silhouette (e.g., "slim fit", "oversized", "A-line")
- `construction`: Chi tiết construction (e.g., "cổ bẻ", "zip closure", "button-down")
- `aesthetic`: Phong cách tổng thể (e.g., "casual", "formal", "minimalist", "vintage")

Each slot SHALL be a nullable string. Empty/null means user did not provide that information.

#### Scenario: Full information query
- **WHEN** user sends "tìm áo sơ mi trắng cotton, dáng slim fit, cổ bẻ, phong cách minimalist"
- **THEN** system extracts: category="Shirt", color="white", fabric="cotton", fit="slim fit", construction="point collar", aesthetic="minimalist"

#### Scenario: Partial information query
- **WHEN** user sends "tìm áo trắng"
- **THEN** system extracts: category="Shirt-like", color="white", fabric=null, fit=null, construction=null, aesthetic=null

#### Scenario: Vague query
- **WHEN** user sends "tìm đồ đẹp"
- **THEN** system extracts: category=null, color=null, fabric=null, fit=null, construction=null, aesthetic=null

### Requirement: Slot extraction integrated into intent classification
The slot extraction SHALL be performed within the existing `classify_intent()` function by extending its prompt and output schema. The system SHALL NOT make a separate LLM call for slot extraction.

#### Scenario: Single LLM call for intent + slots
- **WHEN** user sends any query
- **THEN** system returns intent, confidence, filters, refined_query AND 6 extracted slots in ONE LLM response

### Requirement: Extracted slots data model
The system SHALL define a `ExtractedSlots` data model containing the 6 slot fields (all Optional[str]). This model SHALL be part of the `ClassifiedIntent` return value.

#### Scenario: Slots included in ClassifiedIntent
- **WHEN** classify_intent() returns
- **THEN** result includes an `extracted_slots` field of type `ExtractedSlots`
