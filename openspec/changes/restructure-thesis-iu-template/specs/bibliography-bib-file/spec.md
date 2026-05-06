## ADDED Requirements

### Requirement: bibliography.bib file with all 14 BibTeX entries
The `Report_thesis/` directory SHALL contain a `bibliography.bib` file with all 14 references currently in `main.tex`'s inline `thebibliography` block, converted to valid BibTeX format. Citation keys SHALL be preserved exactly (e.g., `lewis2020rag`, `yao2023react`).

#### Scenario: bibliography.bib contains all entries
- **WHEN** `bibliography.bib` is opened
- **THEN** it contains exactly 14 BibTeX entries with the same keys as the original `\bibitem` entries

### Requirement: main.tex uses external .bib file and ieeetr style
The inline `\begin{thebibliography}{99}...\end{thebibliography}` block in `main.tex` SHALL be replaced with:
```latex
\bibliographystyle{ieeetr}
\bibliography{bibliography.bib}
```
The `\renewcommand{\bibname}{References}` line SHALL be retained immediately before these two lines.

#### Scenario: Bibliography compiles with ieeetr numbering
- **WHEN** `main.tex` is compiled with the 4-pass sequence (pdflatex → bibtex → pdflatex → pdflatex)
- **THEN** the References section in the PDF shows numbered entries `[1]`, `[2]`, ..., `[14]` in ieeetr format
