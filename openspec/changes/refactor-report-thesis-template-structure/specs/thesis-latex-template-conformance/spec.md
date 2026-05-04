## ADDED Requirements

### Requirement: Report thesis source SHALL use modular chapter composition
The `Report_thesis` document SHALL be assembled by a controller LaTeX file that includes chapter bodies via `\input{chapters/...}` instead of storing all chapter content in a single monolithic source file.

#### Scenario: Build assembly uses chapter inputs
- **WHEN** the thesis source is opened for document assembly review
- **THEN** the controller file defines chapter order and references chapter body files under `chapters/` using `\input{...}`

#### Scenario: Existing chapter content is preserved after modularization
- **WHEN** chapter boundaries are migrated from the legacy monolithic source
- **THEN** each original chapter appears exactly once in the modular structure with its content retained

### Requirement: Front-matter list ordering SHALL follow the approved IU template sequence
The report front matter SHALL present navigation/list sections in the following order: Table of Contents, List of Tables, List of Figures, List of Algorithms, List of Listings, then Abstract.

#### Scenario: Ordered front-matter lists are rendered
- **WHEN** the thesis is assembled before main chapters begin
- **THEN** the list pages are declared and rendered in the exact approved sequence

#### Scenario: Abstract follows list pages
- **WHEN** front-matter pages are emitted
- **THEN** the Abstract section appears after List of Listings and before the first numbered chapter

### Requirement: TOC inclusion rules SHALL match approved front-matter behavior
Approval Letter and Acknowledgements SHALL remain present in front matter but SHALL NOT be included in Table of Contents entries. Abstract SHALL be included in the Table of Contents.

#### Scenario: Approval and Acknowledgements are excluded from TOC
- **WHEN** the table of contents is generated
- **THEN** no TOC entries are emitted for Approval Letter or Acknowledgements

#### Scenario: Abstract is included in TOC
- **WHEN** the table of contents is generated
- **THEN** an Abstract entry is present as a front-matter chapter-level TOC item

### Requirement: Abbreviations and symbols lists SHALL be removed from thesis structure
The thesis document structure SHALL not include `List of Abbreviations` or `List of Symbols` sections in the assembled front matter for this change.

#### Scenario: Removed front-matter sections are absent
- **WHEN** the thesis source is assembled with this change
- **THEN** no chapter blocks for List of Abbreviations or List of Symbols are present in the document flow
