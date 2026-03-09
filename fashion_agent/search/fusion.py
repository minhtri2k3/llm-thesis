"""RRF (Reciprocal Rank Fusion) for merging BM25 + Text Vector + Image Vector results."""

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
    text_vec_results: list[NodeWithScore] | None = None,
    k: int = 60,
    bm25_weight: float = 2.5,
    vec_weight: float = 1.0,
    text_vec_weight: float = 1.5,
) -> list[NodeWithScore]:
    """
    Merge BM25, image vector, and text vector results using Reciprocal Rank Fusion.

    Score formula per node:
        rrf_score = bm25_weight     * 1/(k + rank_bm25 + 1)
                  + vec_weight      * 1/(k + rank_img  + 1)
                  + text_vec_weight * 1/(k + rank_text + 1)

    Args:
        bm25_results:      Ranked BM25 results (position = rank).
        vec_results:       Ranked image vector results (position = rank).
        text_vec_results:  Ranked text vector results (optional, for 3-way fusion).
        k:                 RRF constant (default 60).
        bm25_weight:       Weight for BM25 contribution.
        vec_weight:        Weight for image vector contribution.
        text_vec_weight:   Weight for text vector contribution.

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

    # Image vector contributions
    for rank, node in enumerate(vec_results):
        rrf = vec_weight * (1.0 / (k + rank + 1))
        scores[node.image_id] = scores.get(node.image_id, 0.0) + rrf
        if node.image_id not in nodes:
            nodes[node.image_id] = node

    # Text vector contributions (3-way fusion)
    if text_vec_results:
        for rank, node in enumerate(text_vec_results):
            rrf = text_vec_weight * (1.0 / (k + rank + 1))
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
