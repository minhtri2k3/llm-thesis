## ADDED Requirements

### Requirement: Research-context system persona in INTENT_PROMPT
The `INTENT_PROMPT` SHALL begin with a brief paragraph explaining that the agent is operating within a multilingual fashion recommendation research system designed to study LLM recommendation quality and user purchase intent. This context MUST appear before the intent classification instructions.

#### Scenario: LLM understands research context when classifying
- **WHEN** the intent classifier receives a message
- **THEN** the LLM has access to the research framing (thesis, behavioral tracking, VI+EN multilingual)
- **THEN** the LLM's classification behavior is consistent with encouraging product selection interactions

#### Scenario: Research context does not break intent classification
- **WHEN** the research prefix is prepended to INTENT_PROMPT
- **THEN** all 7 intent types (text_search, outfit_request, follow_up, product_select, view_selections, out_of_scope, unclear) continue to be classifiable without degradation

---

### Requirement: Research-context system persona in SYNTHESIS_PROMPT
The `_BASE_SYNTHESIS_PROMPT` SHALL include a brief research-context paragraph stating that the agent is part of a fashion recommendation research study, that user selections are academic data points (not real purchases), and that the agent should encourage users to select products they genuinely prefer.

#### Scenario: LLM synthesis response encourages selection
- **WHEN** the synthesis LLM generates a response to a search result
- **THEN** the response naturally guides the user toward selecting a product number
- **THEN** the response does not mention "purchase", "cart", or real transaction language

#### Scenario: Research context does not inflate response length
- **WHEN** the research persona prefix is added to the synthesis prompt
- **THEN** the synthesis response remains within 2-5 sentences for search intents
- **THEN** the research context is NOT echoed verbatim back to the user in the response

---

### Requirement: Multilingual support is explicit in persona
Both `INTENT_PROMPT` and `_BASE_SYNTHESIS_PROMPT` SHALL explicitly state that the system serves Vietnamese and English users and that all responses MUST be in the same language as the user's message. This requirement SHALL be stated as a hard constraint, not a suggestion.

#### Scenario: Vietnamese user receives Vietnamese synthesis
- **WHEN** user sends a Vietnamese query and the synthesis prompt contains the multilingual constraint
- **THEN** the LLM generates its full response (including CTA) in Vietnamese

#### Scenario: English user receives English synthesis
- **WHEN** user sends an English query
- **THEN** the LLM generates its full response in English with no Vietnamese fragments
