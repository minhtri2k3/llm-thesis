"""
Hybrid search engine: BM25 + Vector → RRF Fusion → Soft Filter → BGE Rerank.

Provides a single `search()` function that orchestrates the full pipeline.
Includes Gemini-powered query expansion for improved recall on short queries.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Optional

from search.fusion import NodeWithScore, reciprocal_rank_fusion
from search.query_expansion import expand_query
from search.reranker import get_reranker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION_NAME = "fashion_products"

BM25_TOP_K = 20
VECTOR_TOP_K = 20
RRF_K = 60
BM25_WEIGHT = 1.0
VEC_WEIGHT = 2.5
SOFT_FILTER_THRESHOLD = 60
RERANK_TOP_K = 6

MODELS_DIR = Path(os.getenv("HF_HOME", "models"))

# ---------------------------------------------------------------------------
# Singleton model holders
# ---------------------------------------------------------------------------

_embedder = None
_bm25_index = None
_bm25_doc_ids = None
_bm25_items = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from indexing.build_index import FashionEmbedder

        _embedder = FashionEmbedder(cache_dir=MODELS_DIR)
    return _embedder


def _load_bm25():
    """Load or build BM25 index from Qdrant payloads."""
    global _bm25_index, _bm25_doc_ids, _bm25_items
    if _bm25_index is not None:
        return

    from qdrant_client import QdrantClient
    from rank_bm25 import BM25Okapi

    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )

    # Scroll all items from Qdrant
    items: list[dict] = []
    offset = None
    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result
        for p in points:
            items.append({
                "image_id": str(p.id),
                **p.payload,
            })
        if next_offset is None:
            break
        offset = next_offset

    # Build BM25 index
    corpus = []
    doc_ids = []
    for item in items:
        text = item.get("bm25_content", "")
        corpus.append(text.lower().split())
        doc_ids.append(item["image_id"])

    _bm25_index = BM25Okapi(corpus)
    _bm25_doc_ids = doc_ids
    _bm25_items = {item["image_id"]: item for item in items}
    print(f"BM25 index loaded with {len(doc_ids)} documents.")


# ---------------------------------------------------------------------------
# Retrievers
# ---------------------------------------------------------------------------

def bm25_retrieve(query: str, top_k: int = BM25_TOP_K) -> list[NodeWithScore]:
    """BM25 keyword search over bm25_content fields."""
    _load_bm25()

    tokens = query.lower().split()
    scores = _bm25_index.get_scores(tokens)

    # Get top-k indices
    scored_indices = sorted(
        enumerate(scores), key=lambda x: x[1], reverse=True
    )[:top_k]

    results = []
    for idx, score in scored_indices:
        if score <= 0:
            continue
        image_id = _bm25_doc_ids[idx]
        item = _bm25_items.get(image_id, {})
        results.append(
            NodeWithScore(
                image_id=image_id,
                label=item.get("label", ""),
                color=item.get("color", ""),
                caption=item.get("caption", ""),
                image_path=item.get("image_path", ""),
                bm25_content=item.get("bm25_content", ""),
                score=score,
            )
        )
    return results


def vector_retrieve(query: str, top_k: int = VECTOR_TOP_K) -> list[NodeWithScore]:
    """Vector ANN search in Qdrant using FashionSigLIP query encoding."""
    from qdrant_client import QdrantClient

    embedder = _get_embedder()
    query_vector = embedder.encode_text(query)

    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    nodes = []
    for hit in results.points:
        payload = hit.payload or {}
        nodes.append(
            NodeWithScore(
                image_id=str(hit.id),
                label=payload.get("label", ""),
                color=payload.get("color", ""),
                caption=payload.get("caption", ""),
                image_path=payload.get("image_path", ""),
                bm25_content=payload.get("bm25_content", ""),
                score=hit.score,
            )
        )
    return nodes


# ---------------------------------------------------------------------------
# Soft relevance filter
# ---------------------------------------------------------------------------

def soft_relevance_filter(
    query: str,
    nodes: list[NodeWithScore],
    threshold: int = SOFT_FILTER_THRESHOLD,
) -> list[NodeWithScore]:
    """
    Filter nodes using RapidFuzz fuzzy string matching on color+category.

    Keeps nodes where fuzzy match score >= threshold.
    """
    from rapidfuzz import fuzz

    query_lower = query.lower()
    filtered = []
    for node in nodes:
        # Check fuzzy match against label and color
        label_score = fuzz.partial_ratio(query_lower, node.label.lower()) if node.label else 0
        color_score = fuzz.partial_ratio(query_lower, node.color.lower()) if node.color else 0
        caption_score = fuzz.partial_ratio(query_lower, node.caption.lower()[:100]) if node.caption else 0

        # Keep if any field matches well enough
        best_score = max(label_score, color_score, caption_score)
        if best_score >= threshold:
            filtered.append(node)

    return filtered


# ---------------------------------------------------------------------------
# Main search function
# ---------------------------------------------------------------------------

def _dedup_merge(nodes: list[NodeWithScore]) -> list[NodeWithScore]:
    """Deduplicate nodes by image_id, keeping the highest score."""
    seen: dict[str, NodeWithScore] = {}
    for node in nodes:
        existing = seen.get(node.image_id)
        if existing is None or node.score > existing.score:
            seen[node.image_id] = node
    return list(seen.values())


def search(
    query: str,
    top_k: int = RERANK_TOP_K,
    use_reranker: bool = True,
    use_soft_filter: bool = True,
    use_query_expansion: bool = True,
) -> list[NodeWithScore]:
    """
    Full hybrid search pipeline:
        0. Query Expansion (Gemini synonyms, short queries only)
        1. BM25 retrieve (top-20 per query)
        2. Vector ANN retrieve (top-20 per query)
        3. Dedup merge by image_id
        4. RRF Fusion
        5. Soft Relevance Filter (optional)
        6. BGE Reranker (optional)

    Args:
        query:                User search query.
        top_k:                Number of final results.
        use_reranker:         Whether to apply BGE reranker.
        use_soft_filter:      Whether to apply fuzzy soft filter.
        use_query_expansion:  Whether to expand query with synonyms.

    Returns:
        List of top-K NodeWithScore, ordered by relevance.
    """
    # Step 0: Query Expansion
    if use_query_expansion:
        queries = expand_query(query)
    else:
        queries = [query]

    # Step 1 & 2: Multi-query dual retrieval
    all_bm25: list[NodeWithScore] = []
    all_vec: list[NodeWithScore] = []
    for q in queries:
        all_bm25.extend(bm25_retrieve(q, top_k=BM25_TOP_K))
        all_vec.extend(vector_retrieve(q, top_k=VECTOR_TOP_K))

    # Step 3: Dedup merge (keep highest score per image_id)
    bm25_deduped = _dedup_merge(all_bm25)
    vec_deduped = _dedup_merge(all_vec)

    # Step 4: RRF Fusion
    fused = reciprocal_rank_fusion(
        bm25_results=bm25_deduped,
        vec_results=vec_deduped,
        k=RRF_K,
        bm25_weight=BM25_WEIGHT,
        vec_weight=VEC_WEIGHT,
    )

    # Step 5: Soft Filter (optional)
    if use_soft_filter and fused:
        filtered = soft_relevance_filter(query, fused)
        # If filter removes everything, keep original (safety net)
        if filtered:
            fused = filtered

    # Step 6: Reranker (optional)
    if use_reranker and fused:
        reranker = get_reranker(cache_dir=MODELS_DIR)
        return reranker.rerank(query, fused, top_k=top_k)

    return fused[:top_k]
