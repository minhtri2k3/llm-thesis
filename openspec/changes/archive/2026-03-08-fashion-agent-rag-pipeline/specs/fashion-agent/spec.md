## ADDED Requirements

### Requirement: Intent Classification
The system SHALL classify user messages into one of: `search`, `recommend`, `chat`, or `clarify` using Gemini LLM.

#### Scenario: Search intent
- **WHEN** user sends "tìm áo sơ mi trắng"
- **THEN** intent is classified as `search` with extracted filters {category: "Shirt", color: "White"}

#### Scenario: Chat intent
- **WHEN** user sends "xin chào, bạn là ai?"
- **THEN** intent is classified as `chat` (no search needed)

### Requirement: Clarification Gate
The system SHALL detect when user query is too vague for meaningful search and ask clarifying questions instead of returning poor results.

#### Scenario: Vague query
- **WHEN** user sends "tìm đồ đẹp"
- **THEN** system responds with clarifying question: "Bạn muốn tìm loại trang phục nào? (áo, quần, váy...) Màu sắc ưa thích?"

#### Scenario: Specific query
- **WHEN** user sends "áo khoác đen da bò"
- **THEN** system proceeds directly to search without clarification

### Requirement: Memory Agent
The system SHALL maintain conversation history per session in PostgreSQL, allowing the agent to reference previous messages.

#### Scenario: New session
- **WHEN** user starts a new conversation
- **THEN** system creates a new session record in `user_sessions` table with a unique session_id

#### Scenario: Context recall
- **WHEN** user says "tìm thêm cái tương tự" after receiving search results
- **THEN** system loads previous messages from `conversation_history` to understand "tương tự" refers to the last search results

### Requirement: Gemini LLM Synthesis
The system SHALL use Gemini 2.5 Pro API to synthesize a natural language response from the top-6 reranked products, user query, and conversation history.

#### Scenario: Search response synthesis
- **WHEN** search pipeline returns 6 products for query "áo sơ mi trắng cho buổi họp"
- **THEN** Gemini produces a structured response containing:
  1. Natural language answer describing top recommendations
  2. Product list with image_id, image_path, label, color, caption, relevance_score
  3. Optional styling suggestions

#### Scenario: No results
- **WHEN** search pipeline returns 0 products
- **THEN** Gemini produces a helpful response suggesting alternative search terms or broader categories

### Requirement: ReAct Loop
The system SHALL implement a ReAct (Reason-Act-Observe) loop allowing the agent to iteratively refine searches based on intermediate results.

#### Scenario: Single-pass success
- **WHEN** first search returns high-confidence results (reranker top score > 0.8)
- **THEN** system proceeds directly to synthesis without re-searching

#### Scenario: Refinement loop
- **WHEN** first search returns low-confidence results (reranker top score < 0.5)
- **THEN** system reasons about why results are poor, generates a refined query, and re-searches (max 2 iterations)
