"""
Hybrid search engine: BM25 + Text Vector + Image Vector → 3-way RRF Fusion → Filter → BGE Rerank.

Provides a single `search()` function that orchestrates the full pipeline.
Includes Gemini-powered query expansion for improved recall on short queries.
Aligned with notebook architecture (RAG_clothes_FashionCLIP2).
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

BM25_TOP_K = 5
VECTOR_TOP_K = 5
TEXT_VEC_TOP_K = 5
RRF_K = 60
BM25_WEIGHT = 2.5
IMG_VEC_WEIGHT = 1.0
TEXT_VEC_WEIGHT = 1.5
MIN_SCORE_THRESHOLD = 0.25  # Items below this blended score are filtered out
SOFT_FILTER_THRESHOLD = 60

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
        https=False,  # Use HTTP for local Docker connection
        prefer_grpc=False,
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


def _vector_retrieve(
    query: str,
    vector_name: str,
    top_k: int,
) -> list[NodeWithScore]:
    """Core Qdrant ANN search parametrized by named vector space."""
    from qdrant_client import QdrantClient

    embedder = _get_embedder()
    query_vector = embedder.encode_text(query)

    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=30,
        https=False,  # Use HTTP for local Docker connection
        prefer_grpc=False,
    )

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using=vector_name,
            limit=top_k,
            with_payload=True,
        )
    except Exception as exc:
        if vector_name != "image":
            # Non-image vectors may be absent in old indexes
            print(f"  Warning: {vector_name} vector search failed (old index?): {exc}")
            return []
        raise

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


def vector_retrieve(query: str, top_k: int = VECTOR_TOP_K) -> list[NodeWithScore]:
    """Vector ANN search using FashionSigLIP image vector space."""
    return _vector_retrieve(query, vector_name="image", top_k=top_k)


def text_vector_retrieve(query: str, top_k: int = TEXT_VEC_TOP_K) -> list[NodeWithScore]:
    """Vector ANN search using text named vector space."""
    return _vector_retrieve(query, vector_name="text", top_k=top_k)


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


def _compute_filter_relevance(
    node: NodeWithScore,
    filters: dict[str, str],
) -> float:
    """Compute filter relevance score [0.0-1.0] based on intent filters.

    When the intent classifier extracts category/color from the query,
    we boost items that match and penalize those that don't.
    """
    from rapidfuzz import fuzz

    scores = []

    # Category match
    cat = filters.get("category", "")
    if cat and node.label:
        cat_score = fuzz.ratio(cat.lower(), node.label.lower()) / 100.0
        scores.append(cat_score)

    # Color match
    color = filters.get("color", "")
    if color and node.color:
        color_score = fuzz.ratio(color.lower(), node.color.lower()) / 100.0
        scores.append(color_score)

    if not scores:
        return 1.0  # No filters to apply
    return sum(scores) / len(scores)


def search(
    query: str,
    top_k: int = 6,
    use_reranker: bool = True,
    use_soft_filter: bool = True,
    use_query_expansion: bool = True,
    filters: Optional[dict[str, str]] = None,
    min_score: float = MIN_SCORE_THRESHOLD,
    min_results: int = 1,
) -> list[NodeWithScore]:
    """
    Full hybrid search pipeline (aligned with notebook architecture):
        0. Query Expansion (Gemini synonyms, short queries only)
        1. BM25 retrieve (top-20 per query)
        2. Image Vector ANN retrieve (top-20 per query)
        3. Text Vector ANN retrieve (top-20 per query)
        4. Dedup merge by image_id per source
        5. 3-way RRF Fusion (BM25=2.5, text_vec=1.5, img_vec=1.0)
        6. Filter-aware scoring / Soft Relevance Filter
        7. BGE Reranker with score blending
        8. Score threshold filter

    Args:
        query:                User search query.
        top_k:                Max number of final results (hard cap).
        use_reranker:         Whether to apply BGE reranker.
        use_soft_filter:      Whether to apply soft filter.
        use_query_expansion:  Whether to expand query with synonyms.
        filters:              Optional intent-extracted filters {"category": ..., "color": ...}.
        min_score:            Minimum blended score to keep (default 0.25).
                              Set to 0.0 to disable threshold filtering.
        min_results:          Always return at least this many results even
                              if their score is below ``min_score``.

    Returns:
        List of up to ``top_k`` NodeWithScore, ordered by relevance.
        May return fewer than ``top_k`` if items fall below ``min_score``.
    """
    # Step 0: Query Expansion
    if use_query_expansion:
        queries = expand_query(query)
    else:
        queries = [query]

    # Step 1-3: Multi-query triple retrieval
    all_bm25: list[NodeWithScore] = []
    all_img_vec: list[NodeWithScore] = []
    all_text_vec: list[NodeWithScore] = []
    for q in queries:
        all_bm25.extend(bm25_retrieve(q, top_k=BM25_TOP_K))
        all_img_vec.extend(vector_retrieve(q, top_k=VECTOR_TOP_K))
        all_text_vec.extend(text_vector_retrieve(q, top_k=TEXT_VEC_TOP_K))

    # Step 4: Dedup merge (keep highest score per image_id per source)
    bm25_deduped = _dedup_merge(all_bm25)
    img_vec_deduped = _dedup_merge(all_img_vec)
    text_vec_deduped = _dedup_merge(all_text_vec)

    # Step 5: 3-way RRF Fusion
    fused = reciprocal_rank_fusion(
        bm25_results=bm25_deduped,
        vec_results=img_vec_deduped,
        text_vec_results=text_vec_deduped if text_vec_deduped else None,
        k=RRF_K,
        bm25_weight=BM25_WEIGHT,
        vec_weight=IMG_VEC_WEIGHT,
        text_vec_weight=TEXT_VEC_WEIGHT,
    )

    # Step 6: Filter-aware scoring or Soft Filter
    if filters and fused:
        # Apply intent-based filter scoring
        for node in fused:
            relevance = _compute_filter_relevance(node, filters)
            node.score *= relevance
        fused.sort(key=lambda n: n.score, reverse=True)
    elif use_soft_filter and fused:
        # Fallback: RapidFuzz soft filter
        filtered = soft_relevance_filter(query, fused)
        if filtered:
            fused = filtered

    # Step 7: Reranker with score blending (optional)
    if use_reranker and fused:
        reranker = get_reranker(cache_dir=MODELS_DIR)
        results = reranker.rerank(query, fused, top_k=top_k)
    else:
        results = fused[:top_k]

    # Step 8: Score threshold filter
    if min_score > 0 and results:
        above = [r for r in results if r.score >= min_score]
        # Guarantee at least min_results items
        if len(above) >= min_results:
            results = above
        else:
            results = results[:max(min_results, len(above))]

    return results
