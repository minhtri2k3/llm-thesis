## ADDED Requirements

### Requirement: Single LISTINGS appendix chapter matching IU template
The appendix section in `main.tex` SHALL use exactly:
```latex
\appendix
\chapter{LISTINGS}
\input{chapters/appendix}
\end{document}
```
The current two-chapter appendix (`Supplementary Equations and Derivations` and `Sample Configuration Files`) SHALL be replaced by this single structure. The custom `\titleformat{\chapter}` override for appendix in `main.tex` SHALL be removed (since the preamble already defines the correct appendix labeling via `\renewcommand{\appendix}`).

#### Scenario: Appendix shows as "Appendix A LISTINGS" in PDF
- **WHEN** `main.tex` is compiled
- **THEN** the appendix chapter heading reads "Appendix A" with title "LISTINGS"

### Requirement: chapters/appendix.tex contains all former appendix content
The new `chapters/appendix.tex` SHALL contain the content from both `chapters/appendix_equations.tex` and `chapters/appendix_configs.tex` via `\input{}` directives, with appropriate section headings to separate the two original appendix chapters.

#### Scenario: appendix.tex includes both former appendix files
- **WHEN** `chapters/appendix.tex` is compiled
- **THEN** content from both `appendix_equations.tex` and `appendix_configs.tex` appears under the LISTINGS chapter
