## ADDED Requirements

### Requirement: LLM Planning sinh kế hoạch tool calls
ReAct orchestrator SHALL dùng Gemini để sinh kế hoạch hành động dạng JSON array, chọn tool nào gọi và với arguments gì, dựa trên query + search results + memory context.

#### Scenario: Planning cho search query
- **WHEN** user gửi "tìm áo sơ mi trắng công sở" và intent = "text_search"
- **THEN** LLM sinh plan `[{"tool": "search", "args": {"query": "white formal shirt"}}]`

#### Scenario: Planning với memory enrichment
- **WHEN** user có history thích "navy blue" và gửi query mơ hồ "tìm áo"
- **THEN** LLM sinh plan `[{"tool": "memory_enrich", "args": {"query": "tìm áo"}}, {"tool": "search", "args": {"query": "<enriched>"}}]`

### Requirement: Tool Registry với 3 tools
Orchestrator SHALL hỗ trợ 3 tools: `search` (hybrid search), `memory_enrich` (bổ sung query từ preferences), `outfit_hints` (gợi ý outfit theo dịp).

#### Scenario: Tool search
- **WHEN** plan chứa `{"tool": "search", "args": {"query": "red dress"}}`
- **THEN** system gọi `hybrid_search("red dress")` và trả kết quả về observation

#### Scenario: Tool memory_enrich
- **WHEN** plan chứa `{"tool": "memory_enrich", "args": {"query": "tìm áo"}}`
- **THEN** system lấy preferences từ memory, bổ sung vào query, trả query mới

#### Scenario: Tool outfit_hints
- **WHEN** plan chứa `{"tool": "outfit_hints", "args": {"occasion": "party"}}`
- **THEN** system sinh gợi ý items phù hợp cho dịp tiệc

### Requirement: Thought-Action-Observation loop max 8 iterations
Mỗi iteration SHALL ghi lại Thought (suy nghĩ), Action (tool call), Observation (kết quả). Max 8 vòng.

#### Scenario: Early exit khi đủ tốt
- **WHEN** iteration 1 trả về kết quả với score > threshold
- **THEN** dừng loop, chuyển sang synthesis

#### Scenario: Retry với query refinement
- **WHEN** iteration 1 trả về score thấp
- **THEN** LLM plan lại với query refined, thử tool khác

#### Scenario: Max iterations reached
- **WHEN** đạt 8 iterations mà chưa tìm đủ
- **THEN** dùng kết quả tốt nhất có được, chuyển sang synthesis

### Requirement: Fallback threshold
Khi không tìm thấy kết quả đủ tốt, orchestrator SHALL hạ relevance threshold -0.2 so với ngưỡng ban đầu.

#### Scenario: Hạ threshold
- **WHEN** sau 4 iterations mà max score < threshold
- **THEN** giảm threshold 0.2, mở rộng kết quả chấp nhận được
