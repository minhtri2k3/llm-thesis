## ADDED Requirements

### Requirement: Unambiguous language detection
The `detect_language()` function SHALL use only unambiguous language-specific tokens for detection. The Spanish pattern SHALL NOT match words that also commonly appear in English text (e.g., `la`, `el`, `un`, `una`, `es`). Spanish detection SHALL rely solely on: special characters (`ñ`, `¿`, `¡`), and unambiguously Spanish words (`quiero`, `necesito`, `busco`, `vestido`, `ropa`, `cómo`, `gracias`, `hola`, `tengo`, `quiero`).

#### Scenario: English text with common Spanish-like words
- **WHEN** user sends `"I want a lace dress in unique minimalist style"`
- **THEN** `detect_language()` SHALL return `"en"` (not `"es"`)

#### Scenario: Unambiguous Spanish text
- **WHEN** user sends `"Quiero un vestido elegante"`
- **THEN** `detect_language()` SHALL return `"es"`

#### Scenario: Spanish with accent characters
- **WHEN** user sends `"¿Tienes algo casual?"`
- **THEN** `detect_language()` SHALL return `"es"`

#### Scenario: Vietnamese detection unchanged
- **WHEN** user sends `"Tôi muốn tìm áo sơ mi"`
- **THEN** `detect_language()` SHALL return `"vi"`

---

### Requirement: Explicit language instruction in synthesis prompt
The synthesis prompt SHALL include an explicit, mandatory language instruction using the detected language name (not as a hint) in the format: `YOU MUST respond exclusively in {language}. Do not use any other language, even if the conversation history contains other languages.`

#### Scenario: English query with Spanish history
- **WHEN** user sends an English query and conversation history contains Spanish messages
- **THEN** the synthesis response SHALL be exclusively in English

#### Scenario: Language variable populated from detection
- **WHEN** `detect_language(query)` returns `"en"`
- **THEN** the synthesis prompt SHALL receive `language = "English"` and include the mandatory instruction

#### Scenario: Vietnamese query
- **WHEN** `detect_language(query)` returns `"vi"`
- **THEN** the synthesis prompt SHALL receive `language = "Vietnamese"` and the response SHALL be in Vietnamese
