## ADDED Requirements

### Requirement: IU-Standard 8-chapter structure in main.tex
The `Report_thesis/main.tex` SHALL replace the current custom chapter block with exactly the 8 IU-mandated chapters in the following order: INTRODUCTION, RELATED WORK, METHODOLOGY, PROTOTYPING, IMPLEMENTATION, RESULT, DISCUSSION, CONCLUSION. The chapter block SHALL begin with `\chapter{INTRODUCTION}` immediately followed by `\pagenumbering{arabic}` and `\setcounter{page}{1}` on the next lines.

#### Scenario: Chapter block matches IU template sequence
- **WHEN** `main.tex` is compiled
- **THEN** the PDF Table of Contents lists exactly 8 numbered chapters in the order: 1 INTRODUCTION, 2 RELATED WORK, 3 METHODOLOGY, 4 PROTOTYPING, 5 IMPLEMENTATION, 6 RESULT, 7 DISCUSSION, 8 CONCLUSION

#### Scenario: Arabic page numbering starts at page 1 on INTRODUCTION
- **WHEN** `main.tex` is compiled
- **THEN** the first page of Chapter 1 (INTRODUCTION) shows page number 1 in Arabic numerals

### Requirement: Content mapping from 11 original files to 8 new IU chapter files
Each of the 8 new IU chapter files SHALL contain (via `\input{}`) all relevant content from the original chapter files according to the following mapping:

| New file | Original source files |
|---|---|
| `chapters/introduction.tex` | `system_overview.tex`, `data_preprocessing.tex` |
| `chapters/work.tex` | `rag_v1_architecture.tex` |
| `chapters/methodology.tex` | `agent_v2_path1.tex` |
| `chapters/prototyping.tex` | `agent_v2_path2.tex`, `end_to_end_example.tex` |
| `chapters/implementation.tex` | `postgresql_integration.tex`, `interface_deployment.tex` |
| `chapters/result.tex` | Lines 1–112 of `evaluation_conclusion.tex` (Evaluation Metrics + Data Collection) |
| `chapters/discussion.tex` | Lines 114–142 of `evaluation_conclusion.tex` (Design Strengths + Risks) |
| `chapters/conclusion.tex` | Lines 144–191 of `evaluation_conclusion.tex` (Conclusion section) |

#### Scenario: introduction.tex contains system overview and data preprocessing content
- **WHEN** `chapters/introduction.tex` is compiled as part of INTRODUCTION chapter
- **THEN** all sections from `system_overview.tex` and `data_preprocessing.tex` appear in the PDF

#### Scenario: result/discussion/conclusion split from evaluation_conclusion.tex
- **WHEN** the three new files are compiled
- **THEN** no content from `evaluation_conclusion.tex` is duplicated or omitted across result, discussion, and conclusion chapters

### Requirement: Original 11 chapter files remain unchanged
The 11 original chapter files SHALL NOT be deleted or modified. They SHALL remain as the content source files that new IU chapter wrappers `\input{}` into.

#### Scenario: Original files still exist after restructuring
- **WHEN** the restructuring tasks are complete
- **THEN** all 11 original `.tex` files in `chapters/` still exist with their original content
