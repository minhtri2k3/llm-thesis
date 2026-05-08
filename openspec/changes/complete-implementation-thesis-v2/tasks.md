## 1. Pre-flight: Cross-check live runtime artefacts before drafting

- [x] 1.1 Read `fashion_agent/docker-compose.yml` for the exact service names, image tags, ports, healthchecks, depends-on edges, and named volumes
- [x] 1.2 Read `fashion_agent/start.sh` for the bootstrap order (DBs up → healthcheck wait → API build/run → public-URL print)
- [x] 1.3 Read `fashion_agent/requirements-docker.txt` to capture pinned versions of Python runtime libraries (FastAPI, Gradio, Qdrant client, psycopg2, open-clip, transformers, etc.)
- [x] 1.4 Read `fashion_agent/agent/prompts.py` to confirm the names and purposes of `INTENT_PROMPT`, `SYNTHESIS_PROMPT`, `STREAM_SYNTHESIS_PROMPT`, `EXPANSION_PROMPT`, `SLOT_TEMPLATES`, `COMBO_TEMPLATES`
- [x] 1.5 Read `fashion_agent/api/main.py` for the SSE event types emitted by `chat_stream` and the FastAPI route table (chat, products, images, sessions, path2, analytics)
- [x] 1.6 Read `fashion_agent/agent/fashion_agent.py:_sse` and the `chat_stream` function for the JSON shape of every SSE `data` payload
- [x] 1.7 Read `clothie_web/lib/services/api_service.dart` (or equivalent) to confirm the API endpoints and event types the Flutter client consumes
- [x] 1.8 Read `fashion_agent/docs/handover.md` for the volume backup/restore commands and the `pgdata_backup.tar.gz` / `qdrant_backup.tar.gz` filenames
- [x] 1.9 Read `fashion_agent/documents/Report_thesis_2/main.tex` to confirm `\includegraphics{IU.png}` uses bare filenames (no `\graphicspath{}`), and that `algorithm`, `algpseudocode`, `booktabs`, `tikz`, `longtable`, `array`, `multirow`, `enumitem`, `float` are loaded
- [x] 1.10 Read `fashion_agent/documents/Report_thesis_2/chapters/methodology.tex` to confirm the stable labels referenced in Implementation (`alg:hybrid_search`, `alg:routing`, `alg:slot_readiness`, `alg:intent_class`, `alg:synthesize_response`, `alg:build_index`, `alg:fashionsiglip`, `eq:rrf`, `fig:workflow_v2`)
- [x] 1.11 Read `fashion_agent/documents/Report_thesis_2/chapters/implementation.tex` to capture the existing chapter intro paragraphs (lines 1--3) so they remain byte-identical after the edit

## 2. Section 4.1: Technical Stack and Environment

- [x] 2.1 Author opening prose framing 4.1 as the runtime inventory complement to Methodology
- [x] 2.2 Author the Component / Version / Role schema table covering Python, FastAPI, Gradio, Pydantic, PostgreSQL 16 Alpine, Qdrant, rank_bm25, RapidFuzz, open-clip + Marqo-FashionSigLIP, transformers + BGE Reranker v2-m3, Gemini 2.5 Flash via `google-generativeai`, Flutter (web), Docker Compose, Cloudflared
- [x] 2.3 Author hardware and device-selection prose (MPS on Apple Silicon, CPU fallback) plus the on-disk size envelope of the cached models under `\texttt{models/}`
- [x] 2.4 Author repository-layout prose pointing to `fashion_agent/`, `clothie_web/`, `qwen_local_rag/` (legacy), and `start.sh`, with a one-sentence purpose per directory

## 3. Section 4.2: Agentic Reasoning and Prompt Engineering

- [x] 3.1 Author opening prose explicitly stating 4.2 covers the prompt artefacts and their parse contract, deferring algorithmic claims to Methodology by `\ref{}`
- [x] 3.2 Author the prompt-artefact contract table (Name / Purpose / Expected JSON shape / Fallback on parse failure) for `INTENT_PROMPT`, `SYNTHESIS_PROMPT`, `STREAM_SYNTHESIS_PROMPT`, `EXPANSION_PROMPT`
- [x] 3.3 Author a brief subsection on multilingual templates: `SLOT_TEMPLATES` and `COMBO_TEMPLATES` keyed by `(missing-slot frozenset, language)` with English / Vietnamese / Spanish coverage
- [x] 3.4 Cite `Algorithm~\ref{alg:intent_class}`, `Algorithm~\ref{alg:slot_readiness}`, `Algorithm~\ref{alg:resolve_search_query}`, and `Algorithm~\ref{alg:synthesize_response}` at the appropriate prose hooks instead of restating their pseudocode
- [x] 3.5 Author a brief failure-modes subsection (malformed JSON, low-confidence drift, unsupported category) describing the deterministic fallback path
- [x] 3.6 Verify zero `\begin{lstlisting}` blocks remain in 4.2

## 4. Section 4.3: Knowledge Base and Vector Indexing (Operational)

- [x] 4.1 Author opening prose explicitly stating 4.3 covers operational details, deferring the index-build algorithm to `Algorithm~\ref{alg:build_index}` and cross-modal encoding to `Algorithm~\ref{alg:fashionsiglip}`
- [x] 4.2 Author the Qdrant collection deployment subsection: collection name, named-vector configuration as actually deployed, payload field list, the BM25 in-memory rebuild on API startup
- [x] 4.3 Author the Postgres deployment subsection: pool sizing (max 5 connections), JSONB column lifecycle on `user_sessions`, and a one-sentence note on schema migration on first startup via `init_memory_tables`
- [x] 4.4 Author the model-cache subsection: layout under `\texttt{models/}` driven by `HF_HOME`, behavior on cold start, pre-download recommendation
- [x] 4.5 Author the volume backup/restore subsection naming `pgdata_backup.tar.gz` and `qdrant_backup.tar.gz` and outlining the restore workflow without embedding shell listings
- [x] 4.6 Verify zero `\begin{lstlisting}` blocks remain in 4.3

## 5. Section 4.4: Multimodal Interface Development

- [x] 5.1 Author Subsection 4.4.1 "Gradio Fallback UI" --- one paragraph plus the screenshot reference `screenshot_path1_clarification.png`, captioned to call out the clarification gate firing and the resulting product gallery
- [x] 5.2 Author Subsection 4.4.2 "Flutter Web Client" --- two paragraphs, the screenshot `screenshot_path1_multilingual.png` (multilingual flow), and the screenshot `screenshot_path2_image_search.png` (PATH 2 image upload)
- [x] 5.3 Author the Flutter $\leftrightarrow$ FastAPI endpoint contract table (Path / Method / Request / Response) covering `/api/chat`, `/api/chat/stream`, `/api/sessions`, `/api/products/{id}`, `/api/images/{filename}`, `/api/path2/image-search`, `/api/sessions/{sid}/selections`, `/health`
- [x] 5.4 Author Subsection 4.4.3 "Streaming Protocol (Server-Sent Events)" --- short prose plus the SSE event-type contract table covering every type currently emitted (`thinking_start`, `thinking_step`, `thinking_end`, `model_thinking`, `token`, `clarification`, `products`, `selection_confirm`, `selection_saved`, `selections_list`, `selection_cancelled`, `done`, `offer_prompt`, `error`) with the JSON schema of each `data` field
- [x] 5.5 Add the screenshot reference `screenshot_sse_streaming.png` inside Subsection 4.4.3, captioned to point out the visible token counters
- [x] 5.6 Confirm every `\includegraphics` uses a bare filename (no path prefix, no extension change) so it sits next to `IU.png`
- [x] 5.7 Verify zero `\begin{lstlisting}` blocks remain in 4.4

## 6. Section 4.5: System Integration and Deployment

- [x] 6.1 Add `\section{System Integration and Deployment}` immediately after Section 4.4 with a brief opening paragraph
- [x] 6.2 Author the Docker Compose service-inventory table (Service / Image / Port / Volumes / Depends-on) for `postgres`, `qdrant`, `fashion-api`, `cloudflared`
- [x] 6.3 Author the TikZ container topology figure with the four services, the port bindings, the depends-on edges, and an arrow from `cloudflared` to a labelled "Public Internet" boundary
- [x] 6.4 Author algorithm `BootstrapClothie` describing the `start.sh` flow (DBs up → wait healthy → build/run API → poll `/health` → print Cloudflare public URL); add `\textit{Source: \texttt{start.sh}}` directly under the caption
- [x] 6.5 Author the env-var reference table (PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD, QDRANT_HOST/QDRANT_PORT/QDRANT_API_KEY, GEMINI_API_KEY, ENABLE_PATH2_IMAGE_SEARCH, SEARCH_CONFIDENCE_THRESHOLD, DATASET_IMAGES_HOST_PATH, HF_HOME, CF_TUNNEL_TOKEN) with their default behaviour and which service consumes them
- [x] 6.6 Author the volume lifecycle subsection clearly distinguishing `docker compose down` (data preserved) from `docker compose down -v` (re-ingest required, cost is multi-hour)
- [x] 6.7 Add a closing paragraph naming the Cloudflare Tunnel exposure pattern and noting that the public URL is printed at the end of `start.sh`
- [x] 6.8 Verify zero `\begin{lstlisting}` blocks remain in 4.5

## 7. Verification (acceptance gates from the spec)

- [x] 7.1 `grep -c '\\begin{lstlisting}' implementation.tex` returns 0
- [x] 7.2 Every `\begin{algorithm}` introduced in 4.5 (and 4.4 if any) is followed within one line by a `\textit{Source: \texttt{...}}` line pointing to a real on-disk path
- [x] 7.3 The chapter intro paragraphs (original lines 1--3) are byte-identical to `git show HEAD:fashion_agent/documents/Report_thesis_2/chapters/implementation.tex` aside from trailing whitespace at section boundaries
- [x] 7.4 Section 4.4 contains exactly four `\includegraphics{...}` directives, each referencing one of `screenshot_path1_clarification.png`, `screenshot_path1_multilingual.png`, `screenshot_path2_image_search.png`, `screenshot_sse_streaming.png` by bare filename
- [x] 7.5 At least one screenshot exercises PATH 1, at least one exercises PATH 2, at least one exercises a non-English language, and at least one shows the SSE streaming surface
- [x] 7.6 Section 4.5 exists with a TikZ container-topology figure and the `BootstrapClothie` algorithm
- [x] 7.7 Every Methodology cross-reference (`\ref{alg:...}`, `\ref{eq:rrf}`, `\ref{fig:workflow_v2}`) resolves under `latexmk` (no "undefined reference" warnings tied to Implementation)
- [x] 7.8 Section 4.4's SSE table covers every event type emitted by `chat_stream()` (cross-checked against the actual `_sse(...)` call sites in `agent/fashion_agent.py`)
- [x] 7.9 `latexmk -pdf Report_thesis_2/main.tex` (run by user) compiles; missing-graphic warnings for the four screenshot placeholders are expected until the user captures them and are not failures
- [x] 7.10 Re-run `openspec validate complete-implementation-thesis-v2 --type change --strict` after edits and confirm no validation errors

## 8. Out-of-scope follow-ups (NOT modified by this change; recorded for the user's later scheduling)

- [x] 8.1 (FOLLOW-UP, NOT this change) `methodology.tex` lines 1--3 still announce "Section 3.7 describes the dataset" / "Section 3.8 defines the evaluation metrics", which contradicts the actual numbering 3.2 (dataset) / 3.6 (evaluation). One-line fix in a future change.
- [x] 8.2 (FOLLOW-UP, NOT this change) `result.tex` still carries pre-thesis numeric thresholds (Recall@5 ≥85% / ≥88%, MRR ≥0.75 / ≥0.80, etc.) that contradict Methodology Section 3.6's "no observed values in Methodology, real numbers in Result". Either replace with measured values plus $N_{query}$ and validity outcomes, or drop the table.
- [x] 8.3 (FOLLOW-UP, NOT this change) `agent_v2_path2.tex` (input by Chapter 4 Prototyping) still uses `\begin{lstlisting}` blocks, which contradicts the chapter-wide "no code listings" policy now in force. Migrate to algorithms / contract tables in a future change.
- [x] 8.4 (FOLLOW-UP, NOT this change) Methodology Section 3.1 still says "shared 512-dimensional latent space" while 3.4 says "768-d". Acknowledged risk in the prior design.md; can be resolved by a one-line edit in 3.1 if the maintainer is comfortable touching the otherwise-frozen 3.1 content.
