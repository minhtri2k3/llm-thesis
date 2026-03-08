"""RRF (Reciprocal Rank Fusion) for merging BM25 + Vector search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeWithScore:
    """A search result node with score and metadata."""

    image_id: str
    label: str = ""
    color: str = ""
    caption: str = ""
    image_path: str = ""
    bm25_content: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


def reciprocal_rank_fusion(
    bm25_results: list[NodeWithScore],
    vec_results: list[NodeWithScore],
    k: int = 60,
    bm25_weight: float = 1.0,
    vec_weight: float = 2.5,
) -> list[NodeWithScore]:
    """
    Merge BM25 and Vector results using Reciprocal Rank Fusion.

    Score formula per node:
        rrf_score = bm25_weight * 1/(k + rank_bm25 + 1)
                  + vec_weight  * 1/(k + rank_vec + 1)

    Args:
        bm25_results: Ranked BM25 results (position = rank).
        vec_results:  Ranked vector results (position = rank).
        k:            RRF constant (default 60).
        bm25_weight:  Weight for BM25 contribution.
        vec_weight:   Weight for vector contribution.

    Returns:
        Merged list sorted by RRF score descending.
    """
    scores: dict[str, float] = {}
    nodes: dict[str, NodeWithScore] = {}

    # BM25 contributions
    for rank, node in enumerate(bm25_results):
        rrf = bm25_weight * (1.0 / (k + rank + 1))
        scores[node.image_id] = scores.get(node.image_id, 0.0) + rrf
        nodes[node.image_id] = node

    # Vector contributions
    for rank, node in enumerate(vec_results):
        rrf = vec_weight * (1.0 / (k + rank + 1))
        scores[node.image_id] = scores.get(node.image_id, 0.0) + rrf
        if node.image_id not in nodes:
            nodes[node.image_id] = node

    # Assign fused scores and sort
    merged = []
    for image_id, score in scores.items():
        node = nodes[image_id]
        node.score = score
        merged.append(node)

    merged.sort(key=lambda n: n.score, reverse=True)
    return merged
