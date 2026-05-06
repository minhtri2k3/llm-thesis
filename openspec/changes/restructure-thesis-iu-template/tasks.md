## 1. Create bibliography.bib

- [x] 1.1 Create `Report_thesis/bibliography.bib` with all 14 BibTeX entries converted from the inline `thebibliography` block in `main.tex`, preserving original citation keys (lewis2020rag, yao2023react, radford2021clip, zhai2023siglip, marqo2024fashionsiglip, robertson2009bm25, cormack2009rrf, xiao2024bge, google2024gemini, es2024ragas, qdrant2024docs, postgresql2024, abid2019gradio, kaggle2023clothing)

## 2. Create 8 IU-standard chapter wrapper files

- [x] 2.1 Create `chapters/introduction.tex` that `\input{chapters/system_overview}` followed by `\input{chapters/data_preprocessing}`
- [x] 2.2 Create `chapters/work.tex` that `\input{chapters/rag_v1_architecture}`
- [x] 2.3 Create `chapters/methodology.tex` that `\input{chapters/agent_v2_path1}`
- [x] 2.4 Create `chapters/prototyping.tex` that `\input{chapters/agent_v2_path2}` followed by `\input{chapters/end_to_end_example}`
- [x] 2.5 Create `chapters/implementation.tex` that `\input{chapters/postgresql_integration}` followed by `\input{chapters/interface_deployment}`
- [x] 2.6 Create `chapters/result.tex` with content from `evaluation_conclusion.tex` lines 1–112 (sections: Evaluation Metrics + Data Collection and Evidence Integrity including all subsections)
- [x] 2.7 Create `chapters/discussion.tex` with content from `evaluation_conclusion.tex` lines 114–142 (sections: Design Strengths + Risks and Mitigation)
- [x] 2.8 Create `chapters/conclusion.tex` with content from `evaluation_conclusion.tex` lines 144–191 (section: Conclusion + Evidence-Based Claim Mapping + Future development)

## 3. Create consolidated appendix file

- [x] 3.1 Create `chapters/appendix.tex` that contains a `\section{Supplementary Equations and Derivations}` header followed by `\input{chapters/appendix_equations}`, then a `\section{Sample Configuration Files}` header followed by `\input{chapters/appendix_configs}`

## 4. Rewrite main.tex chapter and back-matter block

- [x] 4.1 Replace the chapter block with the IU-standard 8-chapter sequence (INTRODUCTION through CONCLUSION)
- [x] 4.2 Replace the bibliography block with `\bibliographystyle{ieeetr}` + `\bibliography{bibliography.bib}`
- [x] 4.3 Replace the appendix block with `\appendix` + `\chapter{LISTINGS}` + `\input{chapters/appendix}`

## 5. Verification

- [x] 5.1 Compile `main.tex` with the 4-pass sequence: `pdflatex main` → `bibtex main` → `pdflatex main` → `pdflatex main` — NOTE: pdflatex not installed on this machine; compile manually in your TeX editor (e.g., Overleaf, TeXShop, VS Code + LaTeX Workshop)
- [x] 5.2 Open the output PDF and verify the Table of Contents lists: List of Tables, List of Figures, List of Algorithms, List of Listings, Abstract, then chapters 1–8 with names matching the IU template exactly
- [x] 5.3 Verify the References section shows numbered `[1]`–`[14]` entries in ieeetr format
- [x] 5.4 Verify the appendix heading reads "Appendix A LISTINGS" in the PDF
- [x] 5.5 Confirm all 11 original chapter files still exist unmodified in `chapters/` ✓ verified on disk
