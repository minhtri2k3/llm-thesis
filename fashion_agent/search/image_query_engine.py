"""PATH 2 image-to-image retrieval pipeline.

This module is intentionally separate from search/search_engine.py so PATH 2
can evolve independently without affecting PATH 1 text-search behavior.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION_NAME = "fashion_products"
MODELS_DIR = Path(os.getenv("HF_HOME", "models"))

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from indexing.build_index import FashionEmbedder

        _embedder = FashionEmbedder(cache_dir=MODELS_DIR)
    return _embedder


def _encode_query_image(raw: bytes) -> list[float]:
    import torch

    embedder = _get_embedder()
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img_tensor = embedder.preprocess_val(img).unsqueeze(0).to(embedder.device)
    with torch.no_grad(), torch.amp.autocast(device_type=embedder.device):
        features = embedder.model.encode_image(img_tensor)
        features /= features.norm(dim=-1, keepdim=True)
    return features.squeeze().cpu().tolist()


def search_by_image_bytes(raw: bytes, top_k: int = 6) -> list[dict]:
    """Return visually similar products for a query image (PATH 2 only)."""
    from qdrant_client import QdrantClient

    query_vector = _encode_query_image(raw)
    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=30,
        https=False,
        prefer_grpc=False,
    )

    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using="image",
        limit=top_k,
        with_payload=True,
    ).points

    products: list[dict] = []
    for hit in hits:
        payload = hit.payload or {}
        products.append(
            {
                "image_id": str(hit.id),
                "image_path": payload.get("image_path", ""),
                "label": payload.get("label", ""),
                "color": payload.get("color", ""),
                "caption": payload.get("caption", ""),
                "score": float(hit.score),
            }
        )
    return products

