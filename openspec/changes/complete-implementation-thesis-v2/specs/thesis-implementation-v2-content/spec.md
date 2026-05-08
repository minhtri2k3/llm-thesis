## ADDED Requirements

### Requirement: Chapter Intro Preserved Verbatim

The system SHALL leave the chapter introduction paragraphs of `implementation.tex` (lines 1--3 of the original file, covering the chapter overview and section roadmap) unchanged.

#### Scenario: Intro paragraphs unchanged after edit
- **WHEN** the implementation completion is applied
- **THEN** the original chapter intro paragraphs (announcing Sections 4.1 through 4.5) are byte-identical to before, except for trivial whitespace at section boundaries

### Requirement: Section 4.1 Technical Stack and Environment

The system SHALL populate Section 4.1 with a stack inventory covering language runtimes, web frameworks, databases, vector store, embedding and reranker models, the LLM client, the mobile/web frontend, and the deployment runtime, with version numbers where applicable.

#### Scenario: Stack inventory table is rendered
- **WHEN** Section 4.1 is compiled
- **THEN** at least one schema-style table appears with columns Component / Version / Role, listing Python, FastAPI, Gradio, PostgreSQL 16, Qdrant, Marqo-FashionSigLIP, BGE Reranker v2-m3, Gemini 2.5 Flash, Flutter (web), Docker Compose, and Cloudflared

#### Scenario: Hardware and model-size context
- **WHEN** Section 4.1 is compiled
- **THEN** the chapter names the device-selection rule (MPS on Apple Silicon, CPU fallback) and the on-disk size envelope of the cached models under `\texttt{models/}` (FashionSigLIP $\sim$1\,GB, BGE Reranker $\sim$1\,GB)

### Requirement: Section 4.2 Agentic Reasoning and Prompt Engineering

The system SHALL populate Section 4.2 with a description of the prompt artefacts under `\texttt{agent/prompts.py}` and the JSON-parse contract with their fallback behaviour, deliberately referencing (not restating) the Methodology algorithms for intent classification, slot readiness, and synthesis.

#### Scenario: Prompt artefact contract table
- **WHEN** Section 4.2 is rendered
- **THEN** a contract table lists `INTENT_PROMPT`, `SYNTHESIS_PROMPT`, `STREAM_SYNTHESIS_PROMPT`, `EXPANSION_PROMPT`, the multilingual `SLOT_TEMPLATES` and `COMBO_TEMPLATES`, with columns covering purpose, expected JSON shape, and the fallback applied on parse failure

#### Scenario: References Methodology algorithms by label
- **WHEN** Section 4.2 discusses orchestration behaviour
- **THEN** it cites `Algorithm~\ref{alg:intent_class}`, `Algorithm~\ref{alg:slot_readiness}`, and `Algorithm~\ref{alg:synthesize_response}` from Methodology rather than restating their pseudocode

#### Scenario: No Python listings
- **WHEN** the rendered Section 4.2 is searched for `\begin{lstlisting}`
- **THEN** the count of matches in 4.2 is zero

### Requirement: Section 4.3 Knowledge Base and Vector Indexing (Operational)

The system SHALL populate Section 4.3 with operational details that complement Methodology Section~3.2: Qdrant collection name and named-vector configuration as deployed, BM25 in-memory rebuild on API startup, Postgres connection-pool sizing, model-cache directory layout, and the volume backup/restore procedure.

#### Scenario: Operational complement, not algorithmic restate
- **WHEN** Section 4.3 is rendered
- **THEN** it references `Algorithm~\ref{alg:build_index}` and `Algorithm~\ref{alg:fashionsiglip}` from Methodology rather than restating them

#### Scenario: Backup/restore procedure documented
- **WHEN** Section 4.3 closes
- **THEN** the chapter names the on-disk backup files (`pgdata_backup.tar.gz`, `qdrant_backup.tar.gz`) and the high-level restore steps without embedding shell-script listings

### Requirement: Section 4.4 Multimodal Interface Development

The system SHALL populate Section 4.4 with three subsections covering the Gradio fallback UI, the Flutter web client, and the Server-Sent-Events streaming protocol, anchored by four screenshot figures.

#### Scenario: Four screenshot placeholders are present
- **WHEN** Section 4.4 is compiled
- **THEN** four `\includegraphics{...}` directives reference, by bare filename, `screenshot_path1_clarification.png`, `screenshot_path1_multilingual.png`, `screenshot_path2_image_search.png`, and `screenshot_sse_streaming.png`, each wrapped in a `figure` environment with a `\caption{}` and `\label{}`

#### Scenario: SSE event-type contract table
- **WHEN** Section 4.4 documents the streaming protocol
- **THEN** a contract table enumerates each event type currently emitted by `chat_stream()` (`thinking_start`, `thinking_step`, `thinking_end`, `model_thinking`, `token`, `clarification`, `products`, `selection_confirm`, `selection_saved`, `selections_list`, `selection_cancelled`, `done`, `offer_prompt`, `error`) with the schema of its `data` field

#### Scenario: PATH 1 vs PATH 2 surfaces both shown
- **WHEN** Section 4.4 is rendered
- **THEN** at least one screenshot exercises PATH 1 (text query) and at least one exercises PATH 2 (image upload)

#### Scenario: Multilingual evidence shown
- **WHEN** Section 4.4 is rendered
- **THEN** at least one screenshot demonstrates the deterministic multilingual clarification branch in Vietnamese or Spanish

### Requirement: Section 4.5 System Integration and Deployment

The system SHALL add a new Section 4.5 covering the Docker Compose container topology, the bootstrap sequence in `start.sh`, public-URL exposure via Cloudflare Tunnel, and the volume lifecycle distinction between `down` and `down -v`.

#### Scenario: Container topology TikZ figure
- **WHEN** Section 4.5 is rendered
- **THEN** a TikZ figure shows the four services (`postgres`, `qdrant`, `fashion-api`, `cloudflared`), their port bindings, depends-on relationships, and the public-URL exposure path through Cloudflare Tunnel

#### Scenario: BootstrapClothie algorithm
- **WHEN** Section 4.5 documents `start.sh`
- **THEN** an `algorithm` environment named `BootstrapClothie` (or equivalent) describes the bootstrap order (DB up $\rightarrow$ healthcheck wait $\rightarrow$ build/run API $\rightarrow$ poll `/health` $\rightarrow$ print public URL) and is followed by `\textit{Source: \texttt{start.sh}}`

#### Scenario: Volume lifecycle and re-ingest cost stated
- **WHEN** Section 4.5 closes
- **THEN** the chapter clearly distinguishes `docker compose down` (data preserved) from `docker compose down -v` (volumes deleted, re-ingest required) and notes the multi-hour re-ingest cost

### Requirement: No Code Listings in Implementation Chapter

Sections 4.1 through 4.5 SHALL contain zero `\begin{lstlisting}` environments, consistent with the Methodology chapter style.

#### Scenario: Zero lstlisting blocks
- **WHEN** the rendered `implementation.tex` is searched for `\begin{lstlisting}`
- **THEN** the count of matches is zero across the entire file

### Requirement: Algorithm Source Citations

Every `algorithm` environment introduced in Sections 4.1 through 4.5 SHALL carry a `\textit{Source: \texttt{...}}` line directly following its caption, naming a real file under the repository.

#### Scenario: Source citation present
- **WHEN** any new algorithm appears in Sections 4.1--4.5
- **THEN** an italicised "Source: <path>" line follows its caption pointing to a real on-disk path (e.g.\ `start.sh`, `agent/prompts.py`)

### Requirement: Methodology Cross-References Use Stable Labels

Implementation references to Methodology algorithms, equations, and figures SHALL use the labels already authored in `methodology.tex` (`alg:hybrid_search`, `alg:routing`, `alg:slot_readiness`, `alg:intent_class`, `alg:synthesize_response`, `alg:build_index`, `alg:fashionsiglip`, `eq:rrf`, `fig:workflow_v2`, etc.).

#### Scenario: References resolve under cross-ref
- **WHEN** `latexmk` runs against the new chapter
- **THEN** no "undefined reference" warnings are emitted for any `\ref{alg:...}`, `\ref{eq:...}`, or `\ref{fig:...}` introduced in Implementation
