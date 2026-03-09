"""
Fashion product embedding & indexing pipeline.

Reads enriched items from PostgreSQL, encodes images with Marqo-FashionSigLIP
(768-dimensional vectors), and upserts into a Qdrant collection. Also builds
an in-memory BM25 index for hybrid retrieval.

Usage:
    python -m indexing.build_index init      # create Qdrant collection
    python -m indexing.build_index build     # encode + upsert + BM25
    python -m indexing.build_index status    # show PG vs Qdrant counts
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import DictCursor
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COLLECTION_NAME = "fashion_products"
VECTOR_SIZE = 768
MODEL_NAME = "Marqo/marqo-fashionSigLIP"
DEFAULT_BATCH_SIZE = 32
DEFAULT_MODELS_DIR = Path("models")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@dataclass
class DBConfig:
    host: str = os.getenv("PGHOST", "localhost")
    port: int = int(os.getenv("PGPORT", "5432"))
    database: str = os.getenv("PGDATABASE", "fashion_rag")
    user: str = os.getenv("PGUSER", "fashion_user")
    password: str = os.getenv("PGPASSWORD", "")


def get_pg_connection(cfg: DBConfig):
    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.user,
        password=cfg.password,
        connect_timeout=5,
    )


def fetch_items_for_indexing(cfg: DBConfig) -> list[dict]:
    """Return items from PG that have both image_path and enrichment data."""
    query = """
    SELECT
        fi.image_id,
        fi.label,
        fi.image_path,
        COALESCE(fe.caption, '') AS caption,
        COALESCE(fe.color, '')   AS color
    FROM fashion_items fi
    LEFT JOIN fashion_item_enrichment fe ON fe.image_id = fi.image_id
    WHERE fi.image_path IS NOT NULL
      AND fi.image_path != ''
    ORDER BY fi.image_id;
    """
    conn = get_pg_connection(cfg)
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def count_pg_items(cfg: DBConfig) -> int:
    conn = get_pg_connection(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fashion_items;")
            return cur.fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

def get_qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )


def init_collection(client, force_recreate: bool = False) -> None:
    """Create Qdrant collection with named vectors (image + text).

    Uses named vector spaces so both image embeddings and text embeddings
    can coexist in the same collection with shared payload.
    """
    from qdrant_client.models import Distance, VectorParams

    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in collections:
        if force_recreate:
            print(f"Deleting existing collection '{COLLECTION_NAME}' for rebuild...")
            client.delete_collection(collection_name=COLLECTION_NAME)
        else:
            print(f"Collection '{COLLECTION_NAME}' already exists. Skipping creation.")
            return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "image": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            "text": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        },
    )
    print(f"Created collection '{COLLECTION_NAME}' with named vectors (image={VECTOR_SIZE}, text={VECTOR_SIZE}).")


def get_existing_point_ids(client) -> set[str]:
    """Return set of image_ids already in Qdrant."""
    from qdrant_client.models import ScrollRequest

    existing: set[str] = set()
    offset = None
    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        points, next_offset = result
        for p in points:
            existing.add(str(p.id))
        if next_offset is None:
            break
        offset = next_offset
    return existing


def count_qdrant_points(client) -> int:
    info = client.get_collection(collection_name=COLLECTION_NAME)
    return info.points_count


# ---------------------------------------------------------------------------
# Embedding model (Marqo-FashionSigLIP)
# ---------------------------------------------------------------------------

class FashionEmbedder:
    """Wraps Marqo-FashionSigLIP for image/text encoding."""

    def __init__(self, model_name: str = MODEL_NAME, cache_dir: Optional[Path] = None):
        import open_clip
        import torch

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Loading {model_name} on device={self.device} ...")

        self.model, self.preprocess_train, self.preprocess_val = (
            open_clip.create_model_and_transforms(
                "ViT-B-16-SigLIP",
                pretrained="webli",
                cache_dir=str(cache_dir) if cache_dir else None,
            )
        )
        # Load Marqo fine-tuned weights
        import huggingface_hub

        ckpt_path = huggingface_hub.hf_hub_download(
            model_name, "open_clip_pytorch_model.bin",
            cache_dir=str(cache_dir) if cache_dir else None,
        )
        state_dict = torch.load(ckpt_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model = self.model.to(self.device).eval()

        self.tokenizer = open_clip.get_tokenizer("ViT-B-16-SigLIP")
        print(f"Model loaded successfully. Device: {self.device}")

    def encode_image(self, image_path: Path) -> list[float]:
        """Encode a single image to a 768-d vector."""
        import torch
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        img_tensor = self.preprocess_val(img).unsqueeze(0).to(self.device)
        with torch.no_grad(), torch.amp.autocast(device_type=self.device):
            features = self.model.encode_image(img_tensor)
            features /= features.norm(dim=-1, keepdim=True)
        return features.squeeze().cpu().tolist()

    def encode_images_batch(
        self, image_paths: list[Path], batch_size: int = DEFAULT_BATCH_SIZE
    ) -> list[list[float]]:
        """Encode a batch of images."""
        import torch
        from PIL import Image

        all_vectors: list[list[float]] = []
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i : i + batch_size]
            tensors = []
            valid_indices = []
            for j, p in enumerate(batch_paths):
                try:
                    img = Image.open(p).convert("RGB")
                    tensors.append(self.preprocess_val(img))
                    valid_indices.append(j)
                except Exception as exc:
                    print(f"  Warning: failed to load {p}: {exc}")
                    all_vectors.append([])  # placeholder

            if tensors:
                batch_tensor = torch.stack(tensors).to(self.device)
                with torch.no_grad(), torch.amp.autocast(device_type=self.device):
                    features = self.model.encode_image(batch_tensor)
                    features /= features.norm(dim=-1, keepdim=True)
                vectors = features.cpu().tolist()

                vec_idx = 0
                result_batch = []
                for j in range(len(batch_paths)):
                    if j in valid_indices:
                        result_batch.append(vectors[vec_idx])
                        vec_idx += 1
                    else:
                        result_batch.append([])
                # replace placeholders
                all_vectors = all_vectors[: i] + result_batch + all_vectors[i + len(batch_paths):]

        return all_vectors

    def encode_text(self, text: str) -> list[float]:
        """Encode a text query to a 768-d vector."""
        import torch

        tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad(), torch.amp.autocast(device_type=self.device):
            features = self.model.encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
        return features.squeeze().cpu().tolist()


# ---------------------------------------------------------------------------
# BM25 index
# ---------------------------------------------------------------------------

def build_bm25_index(items: list[dict]) -> tuple:
    """Build BM25 index from items. Returns (bm25, doc_ids)."""
    from rank_bm25 import BM25Okapi

    corpus: list[list[str]] = []
    doc_ids: list[str] = []
    for item in items:
        bm25_content = compose_bm25_content(item)
        corpus.append(bm25_content.lower().split())
        doc_ids.append(item["image_id"])

    bm25 = BM25Okapi(corpus)
    return bm25, doc_ids


def compose_bm25_content(item: dict) -> str:
    """Compose BM25-searchable text from item metadata.

    Uses only label + color for keyword matching (per notebook research).
    Caption is excluded to avoid noise — it is used separately by the
    cross-encoder reranker.
    """
    label = item.get("label", "")
    color = item.get("color", "")
    parts = []
    if label:
        parts.append(label)
    if color:
        parts.append(color)
    return ". ".join(parts) + "." if parts else ""


def compose_text_embed_content(item: dict) -> str:
    """Compose text for SigLIP text embedding.

    Uses label + color + caption to capture full semantic meaning.
    This mirrors the notebook's text embedding approach where
    full_description was included in embed metadata.
    """
    label = item.get("label", "")
    color = item.get("color", "")
    caption = item.get("caption", "")
    parts = []
    if label:
        parts.append(label)
    if color:
        parts.append(color)
    if caption:
        parts.append(caption)
    return ". ".join(parts) + "." if parts else ""


# ---------------------------------------------------------------------------
# Build command: PG → encode → Qdrant
# ---------------------------------------------------------------------------

def run_build(
    cfg: DBConfig,
    batch_size: int = DEFAULT_BATCH_SIZE,
    cache_dir: Optional[Path] = None,
    limit: Optional[int] = None,
) -> None:
    """Main build pipeline: read PG, encode, upsert to Qdrant."""
    from qdrant_client.models import PointStruct

    print("=== Phase 1: Fetching items from PostgreSQL ===")
    items = fetch_items_for_indexing(cfg)
    print(f"  Found {len(items)} items in PostgreSQL.")

    if not items:
        print("No items to index. Run data ingestion first.")
        return

    # Apply limit for testing
    if limit and limit < len(items):
        items = items[:limit]
        print(f"  Limited to {limit} items for testing.")

    print("=== Phase 2: Connecting to Qdrant ===")
    client = get_qdrant_client()
    init_collection(client)

    existing_ids = get_existing_point_ids(client)
    new_items = [i for i in items if i["image_id"] not in existing_ids]
    print(f"  Already indexed: {len(existing_ids)}, new items: {len(new_items)}")

    if not new_items:
        print("All items already indexed. Nothing to do.")
        print("=== Phase 4: Building BM25 index ===")
        bm25, doc_ids = build_bm25_index(items)
        print(f"  BM25 index built with {len(doc_ids)} documents.")
        return

    print(f"=== Phase 3: Encoding {len(new_items)} images with FashionSigLIP ===")
    embedder = FashionEmbedder(model_name=MODEL_NAME, cache_dir=cache_dir)

    # Process in batches
    points: list = []
    failed = 0
    for i in tqdm(range(0, len(new_items), batch_size), desc="Encoding image batches"):
        batch = new_items[i : i + batch_size]
        image_paths = [Path(item["image_path"]) for item in batch]

        image_vectors = embedder.encode_images_batch(image_paths, batch_size=batch_size)

        for item, img_vec in zip(batch, image_vectors):
            if not img_vec:
                failed += 1
                continue

            # Encode text embedding: label + color + caption
            text_content = compose_text_embed_content(item)
            text_vec = embedder.encode_text(text_content)

            bm25_content = compose_bm25_content(item)
            point = PointStruct(
                id=item["image_id"],
                vector={
                    "image": img_vec,
                    "text": text_vec,
                },
                payload={
                    "image_id": item["image_id"],
                    "label": item["label"],
                    "color": item.get("color", ""),
                    "caption": item.get("caption", ""),
                    "image_path": item["image_path"],
                    "bm25_content": bm25_content,
                },
            )
            points.append(point)

        # Upsert in batches of 100
        if len(points) >= 100:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
            )
            points = []

    # Upsert remaining
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

    total_indexed = count_qdrant_points(client)
    print(f"  Encoding complete. Indexed: {total_indexed}, failed: {failed}")

    print("=== Phase 4: Building BM25 index ===")
    bm25, doc_ids = build_bm25_index(items)
    print(f"  BM25 index built with {len(doc_ids)} documents.")

    print("=== Done ===")


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def run_status(cfg: DBConfig) -> None:
    pg_count = count_pg_items(cfg)
    print(f"PostgreSQL items:  {pg_count}")

    try:
        client = get_qdrant_client()
        qdrant_count = count_qdrant_points(client)
        print(f"Qdrant vectors:    {qdrant_count}")
        diff = pg_count - qdrant_count
        if diff > 0:
            print(f"  → {diff} items not yet indexed.")
        elif diff == 0:
            print("  → All items indexed ✓")
        else:
            print(f"  → Qdrant has {abs(diff)} more vectors than PG items (orphans?).")
    except Exception as exc:
        print(f"Qdrant connection failed: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fashion product embedding & indexing pipeline."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create the Qdrant collection.")

    build_cmd = sub.add_parser("build", help="Encode images and upsert into Qdrant.")
    build_cmd.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Encoding batch size (default: {DEFAULT_BATCH_SIZE}).",
    )
    build_cmd.add_argument(
        "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="Directory for cached HuggingFace models.",
    )
    build_cmd.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of items to index (for testing).",
    )

    sub.add_parser("status", help="Show item counts in PG vs Qdrant.")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = DBConfig()

    if args.command == "init":
        client = get_qdrant_client()
        init_collection(client)
        return

    if args.command == "build":
        run_build(
            cfg=cfg,
            batch_size=args.batch_size,
            cache_dir=Path(args.models_dir),
            limit=args.limit,
        )
        return

    if args.command == "status":
        run_status(cfg)
        return

    print(f"Unknown command: {args.command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
