## Context

`Report_thesis_2/chapters/implementation.tex` has 10 lines: a chapter intro paragraph and four empty `\section{}` headers (4.1--4.4). The intro paragraph also promises a 4.5 ("system integration and deployment strategy") that has no corresponding header. The just-completed Methodology chapter (1015 lines, 25 algorithms, 13 tables, 1 TikZ figure) covers the *what* and *why* of the system in an algorithm-and-table form. Implementation must now cover the *how is it actually built and run* without duplicating Methodology.

The relevant runtime artefacts already exist under `fashion_agent/`:

- `agent/prompts.py` --- the actual `INTENT_PROMPT`, `SYNTHESIS_PROMPT`, `EXPANSION_PROMPT`, multilingual templates.
- `api/main.py` --- FastAPI routes, Gradio mount at `/`, SSE event types (`thinking_start`, `thinking_step`, `thinking_end`, `model_thinking`, `token`, `clarification`, `products`, `selection_confirm`, `selection_saved`, `selections_list`, `done`, `offer_prompt`, `error`).
- `clothie_web/` --- Flutter web frontend that consumes the API at `:8000` and renders the chat / image-upload surfaces.
- `fashion_agent/docker-compose.yml` --- four services (`postgres`, `qdrant`, `fashion-api`, `cloudflared`).
- `start.sh` --- one-command bootstrap from the repo root.
- `docs/handover.md` --- backup/restore commands referencing `pgdata_backup.tar.gz` and `qdrant_backup.tar.gz`.

**Stakeholders**: thesis examiners (need to see deployment is real, not theoretical), the author (must defend operational choices), future maintainers (need ports, env vars, volume names in one place).

## Goals / Non-Goals

**Goals:**

- Produce a self-contained Chapter 4 that an examiner can read after Methodology and immediately understand how the system is built, run, and observed.
- Establish a hard boundary: every algorithmic claim already in Methodology is referenced by label, not restated. Implementation prose talks about versions, ports, file paths, envs, sizes, and observable runtime behaviour.
- Provide four screenshot figures (referenced as `.png` by bare filename, sibling of `IU.png`) so the user can capture later without further file-tree changes.
- Add the TikZ container topology and the SSE event-type table --- both genuinely new content not present in Methodology.

**Non-Goals:**

- Capturing the screenshot images themselves --- the user will produce these after the LaTeX is in place. The change references the filenames; the figures gracefully degrade until images exist.
- Refactoring Methodology, Result, Discussion, or any legacy chapter under `Report_thesis/`.
- Modifying source code, Dockerfiles, prompts, or tests under `fashion_agent/` or `clothie_web/`.
- Backfilling empirical numbers into Result chapter (separate concern).
- Fixing the Methodology chapter intro paragraph that still references the old "3.7 / 3.8" numbering (separate concern).

## Decisions

### D1. Hard separation Methodology vs Implementation

**Decision:** Implementation never restates an algorithm or formula that already appears in Methodology. It only references them by label (`Algorithm~\ref{alg:hybrid_search}`, `Algorithm~\ref{alg:routing}`, `Equation~(\ref{eq:rrf})`, etc.). New algorithm environments are added only when they describe pure operational behaviour (e.g., the `start.sh` bootstrap order) that has no Methodology counterpart.

**Rationale:** Methodology is already 1015 lines. Duplication would bloat the thesis without adding evidence. Reference-by-label respects the reader's working memory and forces Implementation prose to focus on its actual contribution: deployed reality.

**Alternatives considered:**

- *Restate one or two flagship algorithms for self-containment* --- rejected; introduces drift risk and cosmetic redundancy.

### D2. Zero code listings, even in Implementation

**Decision:** Continue the Methodology policy: no `\begin{lstlisting}` environments. All code-shaped content (Docker Compose service definitions, env vars, prompt schemas, API contracts) is rendered as schema tables, contract tables, or short prose with `\texttt{...}` for inline identifiers.

**Rationale:** Consistency with the just-completed Methodology and with the user's standing preference. A thesis chapter is not an engineering handbook; the deployed code lives in Git for any reader who needs it.

**Trade-off:** Some readers expect to see the literal `docker-compose.yml` text. Mitigation: the table format conveys the same information (image, port, volume, dependency) and a `\texttt{docker-compose.yml}` reference points them to the file in Git.

### D3. Section 4.5 is added (chapter intro promises it)

**Decision:** Add `\section{System Integration and Deployment}` after 4.4 to honour the chapter intro paragraph. The intro paragraph itself is left untouched so 4.1--4.5 align verbatim with what it announces.

**Rationale:** The intro paragraph already lists 4.5; adding the header is the smaller intervention. Without 4.5 the chapter would have a content/announcement mismatch that any reviewer notices on first read.

### D4. Four screenshot placeholders, sibling of `IU.png`

**Decision:** All four screenshots live at `Report_thesis_2/<filename>.png` next to the existing `IU.png`, referenced via `\includegraphics{<filename>}` with no path prefix. This matches the pattern used by `IU.png` in `main.tex` (`\includegraphics[width=0.26\textwidth]{IU.png}`).

**Filenames (final):**

| # | Filename | Subject |
|---|----------|---------|
| 1 | `screenshot_path1_clarification.png` | PATH 1 multi-turn: the clarification gate fires, user replies, product gallery renders. |
| 2 | `screenshot_path1_multilingual.png` | Same flow exercised in Vietnamese (or Spanish) demonstrating the 0-LLM deterministic-template branch. |
| 3 | `screenshot_path2_image_search.png` | PATH 2 PNG upload + returned visually similar items. |
| 4 | `screenshot_sse_streaming.png` | Streamed thinking events with intent / synthesis token counter visible to the user. |

**Rationale:** Sibling-of-`IU.png` is the working pattern already in main.tex; no `\graphicspath{}` change required. Bare filenames in `\includegraphics{}` keep the reference style consistent with existing thesis figures. The four chosen subjects are the smallest set that prove the four hardest-to-believe Methodology claims (gate, multilingual templates, image-to-image, streaming) without redundancy.

**Trade-off:** Until the user captures the PNGs, `latexmk` will emit a "file not found" warning per figure. Acceptable: figures degrade to a labelled empty box; the chapter still compiles.

### D5. SSE event-type table is a new contribution

**Decision:** Add a contract table under 4.4 enumerating every SSE event type currently emitted by `chat_stream()` --- `thinking_start`, `thinking_step`, `thinking_end`, `model_thinking`, `token`, `clarification`, `products`, `selection_confirm`, `selection_saved`, `selections_list`, `selection_cancelled`, `done`, `offer_prompt`, `error` --- with the JSON shape of each event's `data` field.

**Rationale:** This information exists nowhere else in the thesis. It is unambiguously the contract between backend and frontend, and a thesis examiner will ask for it. It is also distinctly *not* a Methodology concern (Methodology stops at "the orchestrator yields ThinkingEvents"); the wire format is implementation.

### D6. Container topology rendered as TikZ, not as a screenshot

**Decision:** The four-service Docker Compose layout in 4.5 is a TikZ figure, not a screenshot of `docker compose ps`. Public URL exposure via Cloudflare Tunnel is captured in the same diagram with an arrow from `cloudflared` to the public-internet boundary.

**Rationale:** TikZ scales cleanly with the document, survives a black-and-white print, and does not depend on a particular `docker compose ps` output that drifts each release. The screenshot budget of four is reserved for user-facing surfaces where the screenshot is itself the evidence; deployment topology is better drawn.

### D7. `start.sh` flow as an algorithm

**Decision:** The `start.sh` bootstrap in 4.5 is rendered as one short `algorithm` environment titled `BootstrapClothie` with a Source line pointing to the repo-root `start.sh`. This is the only new algorithm in the Implementation chapter; everything else cross-references existing Methodology algorithms.

**Rationale:** `start.sh` has no Methodology counterpart (it is operational, not analytical) but has enough sequential branching ("DBs healthy --> build/run --> wait /health --> print public URL") that prose alone obscures the order. The algorithm form keeps it precise without resorting to a shell-script listing.

## Risks / Trade-offs

- **[Screenshot lag]**: Until the user captures the four PNGs, the chapter compiles with placeholder warnings. *Mitigation*: the LaTeX renders gracefully; the captions stand on their own as descriptions of what the figure is showing once captured.
- **[Drift between Implementation prose and live code]**: Versions and port numbers can change. *Mitigation*: each runtime claim cites a single source file (`docker-compose.yml`, `requirements-docker.txt`, `start.sh`) so a future maintainer can grep for the discrepancy.
- **[Cross-reference rot if Methodology is renumbered]**: All Methodology label references (`alg:hybrid_search`, etc.) are stable as long as the existing labels remain in `methodology.tex`. *Mitigation*: those labels are what we authored last change; a future Methodology edit should preserve them.
- **[Bare-filename graphics]**: `\includegraphics{IU.png}` works only when the working directory at compile time is `Report_thesis_2/`. *Mitigation*: this is already the pattern; the existing `IU.png` works, so the four new files will resolve identically. No `\graphicspath{}` introduced.
- **[Out-of-scope drifts left untouched]**: The Methodology intro paragraph still references "Section 3.7" and "Section 3.8"; `result.tex` still carries pre-thesis numeric thresholds; `agent_v2_path2.tex` still has `lstlisting` blocks. These are flagged in tasks.md as follow-ups for the user to schedule but are explicitly **not modified by this change**.

## Migration Plan

1. Apply edits to `implementation.tex` only.
2. User captures four PNG screenshots and drops them into `Report_thesis_2/` (sibling of `IU.png`).
3. User compiles `Report_thesis_2/main.tex` with `pdflatex` / `latexmk` and reviews the rendered PDF.
4. Rollback strategy: `git checkout HEAD -- fashion_agent/documents/Report_thesis_2/chapters/implementation.tex`. The chapter is a single file; reversion is one command. The four PNG files are user-managed assets; they remain untouched by a chapter rollback.

## Open Questions

- Should the SSE event-type table list every event currently emitted, or only the four "happy path" ones (`thinking_*`, `products`, `token`, `done`)? **Default**: list all of them in a compact table; it is a contract and partial coverage misleads.
- Should `4.4` cite specific Flutter widget classes (e.g., `ChatBubble`, `ProductCard`) or stay framework-agnostic? **Default**: stay framework-agnostic in prose, with a single `\texttt{clothie\_web/lib/...}` pointer per surface --- enough breadcrumb without the chapter becoming Flutter-specific.
- The fourth screenshot (`screenshot_sse_streaming.png`) could alternatively be a deployment screenshot (`docker compose ps` + Cloudflare URL). **Default kept**: SSE streaming, because it ties a Methodology claim ("streaming with thinking events") to user-visible evidence; deployment is already covered by the TikZ in 4.5.
