"""
Restore fashion_items + fashion_item_enrichment tables from Qdrant payloads.
Run inside the fashion-api container.
"""
import os
import psycopg2
from psycopg2.extras import execute_batch
from qdrant_client import QdrantClient

conn = psycopg2.connect(
    host=os.getenv("PGHOST", "postgres"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "fashion_rag"),
    user=os.getenv("PGUSER", "fashion_user"),
    password=os.getenv("PGPASSWORD", ""),
    connect_timeout=5,
)
conn.autocommit = False

with conn.cursor() as cur:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fashion_items (
        image_id   TEXT PRIMARY KEY,
        label      TEXT NOT NULL,
        image_path TEXT NOT NULL,
        source     TEXT DEFAULT 'restored',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_fashion_items_label ON fashion_items(label);

    CREATE TABLE IF NOT EXISTS fashion_item_enrichment (
        image_id         TEXT PRIMARY KEY REFERENCES fashion_items(image_id) ON DELETE CASCADE,
        caption          TEXT,
        color            TEXT,
        caption_model    TEXT,
        color_model      TEXT,
        last_captioned_at TIMESTAMPTZ,
        last_colored_at  TIMESTAMPTZ,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS fashion_processing_logs (
        id         BIGSERIAL PRIMARY KEY,
        image_id   TEXT NOT NULL,
        step       TEXT NOT NULL,
        status     TEXT NOT NULL,
        message    TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    conn.commit()
    print("Tables created (or already exist).")

# Pull every point from Qdrant and upsert into PG
client = QdrantClient(host="qdrant", port=6333, timeout=60, https=False, prefer_grpc=False)

offset = None
total_items = 0
total_enriched = 0

with conn.cursor() as cur:
    while True:
        result = client.scroll(
            collection_name="fashion_products",
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result

        item_rows = []
        enrich_rows = []

        for p in points:
            pl = p.payload or {}
            iid = str(p.id)
            label = pl.get("label") or "Unknown"
            image_path = pl.get("image_path") or f"{iid}.jpg"
            item_rows.append((iid, label, image_path, "qdrant_restore"))

            caption = pl.get("caption") or ""
            color = pl.get("color") or ""
            if caption or color:
                enrich_rows.append((iid, caption or None, color or None))

        if item_rows:
            execute_batch(
                cur,
                """
                INSERT INTO fashion_items (image_id, label, image_path, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (image_id) DO NOTHING
                """,
                item_rows,
            )
            total_items += len(item_rows)

        if enrich_rows:
            execute_batch(
                cur,
                """
                INSERT INTO fashion_item_enrichment (image_id, caption, color)
                VALUES (%s, %s, %s)
                ON CONFLICT (image_id) DO NOTHING
                """,
                enrich_rows,
            )
            total_enriched += len(enrich_rows)

        conn.commit()
        print(f"  Batch done — cumulative items: {total_items}, enriched: {total_enriched}")

        if next_offset is None:
            break
        offset = next_offset

print(f"\nDone. Restored {total_items} items, {total_enriched} with enrichments.")
conn.close()
