import os
import torch
import open_clip
from pathlib import Path
from tqdm import tqdm
from qdrant_client.models import PointVectors

from indexing.build_index import (
    fetch_items_for_indexing, 
    get_qdrant_client, 
    FashionEmbedder, 
    compose_text_embed_content, 
    compose_bm25_content,
    DBConfig,
    COLLECTION_NAME,
    MODEL_NAME
)

def update_text_index():
    cfg = DBConfig()
    print("Fetching items from PostgreSQL...")
    items = fetch_items_for_indexing(cfg)
    print(f"Found {len(items)} items.")

    client = get_qdrant_client()
    
    print("Loading text embedder...")
    embedder = FashionEmbedder(model_name=MODEL_NAME)
    
    batch_size = 100
    failed = 0
    updated = 0
    
    print("Re-encoding texts and updating Qdrant payloads & text vectors...")
    for i in tqdm(range(0, len(items), batch_size)):
        batch = items[i:i+batch_size]
        try:
            # 1. New Payload
            for item in batch:
                bm25_content = compose_bm25_content(item)
                payload = {
                    "image_id": item["image_id"],
                    "label": item["label"],
                    "color": item.get("color", ""),
                    "caption": item.get("caption", ""),
                    "image_path": item["image_path"],
                    "bm25_content": bm25_content,
                }
                client.set_payload(
                    collection_name=COLLECTION_NAME,
                    payload=payload,
                    points=[item["image_id"]],
                    wait=False
                )
            
            # 2. Batch text encoding
            texts = [compose_text_embed_content(item) for item in batch]
            
            # encode batch manually
            tokens = embedder.tokenizer(texts).to(embedder.device)
            with torch.no_grad(), torch.amp.autocast(device_type=embedder.device):
                features = embedder.model.encode_text(tokens)
                features /= features.norm(dim=-1, keepdim=True)
            text_vecs = features.cpu().tolist()
            
            # 3. Update vectors
            point_vectors = []
            for item, vec in zip(batch, text_vecs):
                point_vectors.append(PointVectors(id=item["image_id"], vector={"text": vec}))
                
            client.update_vectors(
                collection_name=COLLECTION_NAME,
                points=point_vectors,
            )
            updated += len(batch)
            
        except Exception as e:
            print(f"Failed to update batch: {e}")
            failed += len(batch)
            
    print(f"Finished! Updated {updated} items. Failed {failed}.")

if __name__ == "__main__":
    update_text_index()
