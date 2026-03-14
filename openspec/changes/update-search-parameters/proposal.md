## Why

Currently, the search engine utilizes `BM25_TOP_K`, `VECTOR_TOP_K`, and `TEXT_VEC_TOP_K` all set to 20, retrieving up to 60 results (or more with query expansion) for Reciprocal Rank Fusion (RRF). These merged results are then passed to the BGE reranker which selects up to 20 top items and ultimately returning the top 6 (`RERANK_TOP_K = 6`). 
By reducing the number of initially retrieved results per channel to 5, we can significantly decrease latency and computation footprint. Furthermore, setting the final reranker output sequence to 3 results reduces the context size passed into the Gemini LLM. A smaller context size generally leads to faster text generation and more focused, accurate responses.

## What Changes

- Modify `BM25_TOP_K` from 20 to 5.
- Modify `VECTOR_TOP_K` from 20 to 5.
- Modify `TEXT_VEC_TOP_K` from 20 to 5.
- Modify `RERANK_TOP_K` from 6 to 3.
- All modifications are configuration adjustments within `fashion_agent/search/search_engine.py`.

## Capabilities

### New Capabilities
- `search-param-optimization`: Narrow the top-k constraint variables to enforce a faster, leaner pipeline for search and reranking.

### Modified Capabilities


## Impact

- Codebase modified: `fashion_agent/search/search_engine.py`.
- System Performance: Noticeably lower end-to-end latency during retrieval and execution of the final Reranker block. 
- LLM Output: Focus shifted towards synthesizing answers based strictly on 3 highly relevant nodes rather than 6.
