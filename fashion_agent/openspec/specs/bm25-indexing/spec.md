## MODIFIED Requirements

### Requirement: BM25 content composition
The `compose_bm25_content()` function SHALL compose BM25-searchable text using ONLY `label` and `color` fields. Caption MUST NOT be included in BM25 content.

#### Scenario: BM25 content format
- **WHEN** an item has label="T-Shirt" and color="Olive Green"
- **THEN** `compose_bm25_content()` MUST return `"T-Shirt. Olive Green."`
- **AND** the output MUST NOT contain any caption text

#### Scenario: Missing color
- **WHEN** an item has label="Dress" but color is empty
- **THEN** `compose_bm25_content()` MUST return `"Dress."`

#### Scenario: Missing both
- **WHEN** an item has neither label nor color
- **THEN** `compose_bm25_content()` MUST return an empty string `""`

### Requirement: Qdrant payload bm25_content field
After re-indexing, the `bm25_content` field stored in Qdrant payloads MUST contain only `label + color`, consistent with `compose_bm25_content()`.

#### Scenario: Re-index updates bm25_content
- **WHEN** `build_index.py build` is executed after the fix
- **THEN** all Qdrant points MUST have `bm25_content` field containing only `label. color.` format
- **AND** caption MUST remain available in a separate `caption` payload field for reranker use
