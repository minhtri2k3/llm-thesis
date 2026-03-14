## Context

The system currently retrieves up to 20 documents per retrieval channel (BM25, Image Vector, Text Vector). This translates to potentially high computational latency as these items all pass through an intensive BGE Reranker model, which processes up to 20 items to output 6 final items. Small reductions in these upper bounds will directly lower the execution latency.

## Goals / Non-Goals

**Goals:**
- Substantially decrease the response latency in the search operation by cutting out candidate evaluation.
- Reduce the LLM's context processing load by feeding fewer, clearer top choices, maintaining overall relevance of highest-ranked results while discarding noise.

**Non-Goals:**
- Switching out or upgrading the core embedding (SigLIP) or reranking (BGE v2) models.
- Altering Qdrant vectors or DB component setups directly.

## Decisions

- Top K limits for upstream retrieval branches (`BM25_TOP_K`, `VECTOR_TOP_K`, `TEXT_VEC_TOP_K`) will change from 20 to 5.
- The terminal output bound accepted by LLM context (`RERANK_TOP_K`) will reduce from 6 down to 3. 
- These changes require adjustment of global constants inside `fashion_agent/search/search_engine.py`.

## Risks / Trade-offs

- Eliminating base retrieval candidates reduces search recall. A highly relevant document ranked beyond 5 in the initial vector query will be lost early before reaching the more capable reranking sequence. This incurs a deliberate Recall vs. Speed trade-off.
