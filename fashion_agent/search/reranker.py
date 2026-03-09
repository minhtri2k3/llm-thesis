"""BGE Reranker v2-m3 wrapper for cross-encoder reranking."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from search.fusion import NodeWithScore


# Singleton instance
_reranker_instance = None


class BGEReranker:
    """Cross-encoder reranker using BAAI/bge-reranker-v2-m3."""

    MODEL_NAME = "BAAI/bge-reranker-v2-m3"
    MAX_INPUT_DOCS = 20

    def __init__(self, cache_dir: Optional[Path] = None):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Loading BGE Reranker on device={self.device} ...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.MODEL_NAME,
            cache_dir=str(cache_dir) if cache_dir else None,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.MODEL_NAME,
            cache_dir=str(cache_dir) if cache_dir else None,
            torch_dtype=torch.float16,
        ).to(self.device).eval()

        print("BGE Reranker loaded successfully.")

    def rerank(
        self,
        query: str,
        nodes: list[NodeWithScore],
        top_k: int = 6,
    ) -> list[NodeWithScore]:
        """
        Rerank nodes using cross-encoder scoring.

        Args:
            query:  User search query.
            nodes:  Candidate nodes to rerank.
            top_k:  Number of top results to return.

        Returns:
            Top-K nodes sorted by reranker score descending.
        """
        import torch

        if not nodes:
            return []

        # Limit input to MAX_INPUT_DOCS to control latency
        candidates = nodes[: self.MAX_INPUT_DOCS]

        # Build (query, document) pairs
        pairs = []
        for node in candidates:
            doc_text = _compose_doc_text(node)
            pairs.append((query, doc_text))

        # Tokenize
        inputs = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(self.device)

        # Score
        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = outputs.logits.squeeze(-1).cpu().tolist()

        # Handle single item case
        if isinstance(scores, float):
            scores = [scores]

        # Assign scores and sort
        for node, score in zip(candidates, scores):
            node.score = score

        candidates.sort(key=lambda n: n.score, reverse=True)
        return candidates[:top_k]


def _compose_doc_text(node: NodeWithScore) -> str:
    """Compose document text for the reranker from node metadata."""
    parts = []
    if node.label:
        parts.append(node.label)
    if node.color:
        parts.append(node.color)
    if node.caption:
        parts.append(node.caption)
    return ". ".join(parts) if parts else node.bm25_content


def get_reranker(cache_dir: Optional[Path] = None) -> BGEReranker:
    """Get or create singleton reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BGEReranker(cache_dir=cache_dir)
    return _reranker_instance
