"""
Database-first fashion preprocessing pipeline.

Connects to local PostgreSQL (Docker Compose or native).

Main capabilities:
1. Initialize processing tables in PostgreSQL.
2. Upsert fashion items into `fashion_items`.
3. Generate caption/color for items that are still missing enrichment fields.

Usage examples:
    python3 pre_processing/processing_data.py init-db
    python3 pre_processing/processing_data.py doctor
    python3 pre_processing/processing_data.py upsert-item \
        --image-id 123 --label "Shirt" --image-path /data/images/123.jpg
    python3 pre_processing/processing_data.py process \
        --images-dir /data/images --captions --colors --limit 200
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import psycopg2
from psycopg2.extras import DictCursor, execute_batch
from PIL import Image
from tqdm import tqdm


DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
REQUIRED_DB_ENV = ("PGDATABASE", "PGUSER", "PGPASSWORD")
KAGGLE_DATASET_DEFAULT = "agrigorev/clothing-dataset-full"
EXCLUDED_LABELS = {"Not sure", "Skip", "Other"}


@dataclass
class DatabaseConfig:
    host: str = field(default_factory=lambda: os.getenv("PGHOST", DEFAULT_DB_HOST))
    port: int = field(default_factory=lambda: int(os.getenv("PGPORT", str(DEFAULT_DB_PORT))))
    database: Optional[str] = field(default_factory=lambda: os.getenv("PGDATABASE"))
    user: Optional[str] = field(default_factory=lambda: os.getenv("PGUSER"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("PGPASSWORD"))


def required_env_template() -> str:
    return (
        'export PGDATABASE="fashion_rag"\n'
        'export PGUSER="fashion_user"\n'
        'export PGPASSWORD="<your-db-password>"\n'
        'export PGHOST="localhost"\n'
        'export PGPORT="5432"'
    )


def validate_required_db_env(config: DatabaseConfig) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not config.database:
        missing.append("PGDATABASE")
    if not config.user:
        missing.append("PGUSER")
    if not config.password:
        missing.append("PGPASSWORD")
    return (len(missing) == 0), missing


def print_missing_env_help(missing: list[str]) -> None:
    print(f"[FAIL] Missing required environment variable(s): {', '.join(missing)}")
    print("Set environment variables using this template:")
    print(required_env_template())





def check_postgres_login(config: DatabaseConfig) -> tuple[bool, str]:
    env_ok, missing = validate_required_db_env(config)
    if not env_ok:
        return False, f"Missing env vars: {', '.join(missing)}"

    try:
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            dbname=config.database,
            user=config.user,
            password=config.password,
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return True, "PostgreSQL login + SELECT 1 successful"
    except Exception as exc:
        return False, str(exc)
    


def print_check(name: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")


def run_doctor(config: DatabaseConfig) -> int:
    """Run connectivity diagnostics for PostgreSQL (local/Docker)."""
    print("=" * 60)
    print("Fashion Agent — Database Diagnostics")
    print(f"  PGHOST     = {config.host!r}")
    print(f"  PGPORT     = {config.port!r}")
    print(f"  PGDATABASE = {config.database!r}")
    print(f"  PGUSER     = {config.user!r}")
    print(f"  PGPASSWORD = {'***' if config.password else 'NOT SET'}")
    print("=" * 60)

    env_ok, missing = validate_required_db_env(config)
    if not env_ok:
        print_check("env_vars", False, f"Missing: {', '.join(missing)}")
        print_missing_env_help(missing)
        print("Doctor result: FAIL")
        return 2

    print_check("env_vars", True, "All required env vars present")

    pg_ok, pg_detail = check_postgres_login(config)
    print_check("postgres_login", pg_ok, pg_detail)
    if not pg_ok:
        print("[FAIL] PostgreSQL connection failed.")
        print(f"  Error: {pg_detail}")
        print("  Tips:")
        print("    - Is PostgreSQL running? (docker compose up -d postgres)")
        print(f"    - Is it reachable at {config.host}:{config.port}?")
        print("    - Are PGUSER / PGPASSWORD correct?")
        print("Doctor result: FAIL")
        return 1

    print("Doctor result: PASS")
    return 0


class FashionDatabase:
    """Lightweight PostgreSQL client for the fashion preprocessing pipeline."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> None:
        if self.conn and not self.conn.closed:
            return

        assert self.config.database is not None
        assert self.config.user is not None
        assert self.config.password is not None

        self.conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.database,
            user=self.config.user,
            password=self.config.password,
            connect_timeout=5,
        )
        self.conn.autocommit = False

    def close(self) -> None:
        if self.conn and not self.conn.closed:
            self.conn.close()

    def init_tables(self) -> None:
        assert self.conn is not None, "Database is not connected."
        ddl = """
        CREATE TABLE IF NOT EXISTS fashion_items (
            image_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            image_path TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_fashion_items_label
            ON fashion_items(label);

        CREATE TABLE IF NOT EXISTS fashion_item_enrichment (
            image_id TEXT PRIMARY KEY REFERENCES fashion_items(image_id) ON DELETE CASCADE,
            caption TEXT,
            color TEXT,
            caption_model TEXT,
            color_model TEXT,
            last_captioned_at TIMESTAMPTZ,
            last_colored_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fashion_processing_logs (
            id BIGSERIAL PRIMARY KEY,
            image_id TEXT NOT NULL,
            step TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_fashion_processing_logs_image_id
            ON fashion_processing_logs(image_id);
        """
        with self.conn.cursor() as cur:
            cur.execute(ddl)
        self.conn.commit()

    def upsert_items(self, rows: Iterable[tuple[str, str, str, str]]) -> None:
        assert self.conn is not None, "Database is not connected."
        sql = """
        INSERT INTO fashion_items (image_id, label, image_path, source)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (image_id) DO UPDATE SET
            label = EXCLUDED.label,
            image_path = EXCLUDED.image_path,
            source = EXCLUDED.source,
            updated_at = NOW();
        """
        with self.conn.cursor() as cur:
            execute_batch(cur, sql, rows, page_size=100)
        self.conn.commit()

    def fetch_missing_captions(self, limit: int) -> list[dict]:
        assert self.conn is not None, "Database is not connected."
        query = """
        SELECT fi.image_id, fi.label, fi.image_path
        FROM fashion_items fi
        LEFT JOIN fashion_item_enrichment fe ON fe.image_id = fi.image_id
        WHERE fe.caption IS NULL OR BTRIM(fe.caption) = ''
        ORDER BY fi.image_id
        LIMIT %s;
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (limit,))
            records = cur.fetchall()
        return [dict(r) for r in records]

    def fetch_missing_colors(self, limit: int) -> list[dict]:
        assert self.conn is not None, "Database is not connected."
        query = """
        SELECT fi.image_id, fi.label, fi.image_path
        FROM fashion_items fi
        LEFT JOIN fashion_item_enrichment fe ON fe.image_id = fi.image_id
        WHERE fe.color IS NULL OR BTRIM(fe.color) = ''
        ORDER BY fi.image_id
        LIMIT %s;
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (limit,))
            records = cur.fetchall()
        return [dict(r) for r in records]

    def upsert_caption(self, image_id: str, caption: str, model_name: str) -> None:
        assert self.conn is not None, "Database is not connected."
        query = """
        INSERT INTO fashion_item_enrichment (
            image_id, caption, caption_model, last_captioned_at, updated_at
        )
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (image_id) DO UPDATE SET
            caption = EXCLUDED.caption,
            caption_model = EXCLUDED.caption_model,
            last_captioned_at = NOW(),
            updated_at = NOW();
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (image_id, caption, model_name))
        self.conn.commit()

    def upsert_color(self, image_id: str, color: str, model_name: str) -> None:
        assert self.conn is not None, "Database is not connected."
        query = """
        INSERT INTO fashion_item_enrichment (
            image_id, color, color_model, last_colored_at, updated_at
        )
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (image_id) DO UPDATE SET
            color = EXCLUDED.color,
            color_model = EXCLUDED.color_model,
            last_colored_at = NOW(),
            updated_at = NOW();
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (image_id, color, model_name))
        self.conn.commit()

    def log(self, image_id: str, step: str, status: str, message: str) -> None:
        assert self.conn is not None, "Database is not connected."
        query = """
        INSERT INTO fashion_processing_logs (image_id, step, status, message)
        VALUES (%s, %s, %s, %s);
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (image_id, step, status, message))
        self.conn.commit()


class GeminiFashionProcessor:
    def __init__(self, api_key: str, model_name: str = DEFAULT_GEMINI_MODEL) -> None:
        self.model_name = model_name
        self.model = self._build_model(api_key, model_name)

    @staticmethod
    def _build_model(api_key: str, model_name: str):
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: google-generativeai. "
                "Install with `pip install google-generativeai`."
            ) from exc

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)

    def generate_search_caption(self, image_path: Path) -> Optional[str]:
        prompt = """
        Write a 30-40 word fashion-centric morphological description.
        Focus:
        1. Fabric / Texture
        2. Silhouette / Fit
        3. Construction details (collars, seams, closures)
        4. Overall aesthetic

        Rules:
        - Use professional fashion vocabulary
        - NO colors
        - NO brand names
        - NO generic category names
        - Single paragraph only
        """
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([prompt, img])
            if not response.text:
                return None
            return response.text.strip().replace("\n", " ").replace("*", "")
        except Exception:
            return None

    def detect_item_color(self, image_path: Path, label: str) -> Optional[str]:
        prompt = f"""
        Identify the primary color of this {label}.
        Rules:
        1. Return only the color name(s).
        2. Be specific (e.g., 'Olive Green' instead of 'Green', 'Charcoal Grey' instead of 'Grey').
        3. If it has a pattern, mention the base color and the pattern type (e.g., 'White with Black stripes').
        4. Max 3-4 words. No full sentences.
        """
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([prompt, img])
            if not response.text:
                return None
            return response.text.strip().replace("*", "")
        except Exception:
            return None


def resolve_image_path(row: dict, images_dir: Optional[Path]) -> Path:
    raw_path = (row.get("image_path") or "").strip()
    if raw_path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        if images_dir:
            candidate = images_dir / raw_path
            if candidate.exists():
                return candidate
        return path

    if images_dir:
        return images_dir / f"{row['image_id']}.jpg"

    return Path(f"{row['image_id']}.jpg")


def process_missing_captions(
    db: FashionDatabase,
    processor: GeminiFashionProcessor,
    images_dir: Optional[Path],
    limit: int,
    sleep_seconds: float,
) -> int:
    rows = db.fetch_missing_captions(limit=limit)
    if not rows:
        print("No rows with missing caption.")
        return 0

    updated = 0
    for row in tqdm(rows, desc="Generating captions"):
        image_id = row["image_id"]
        image_path = resolve_image_path(row, images_dir)
        if not image_path.exists():
            db.log(image_id, "caption", "skipped", f"missing_image:{image_path}")
            continue

        caption = processor.generate_search_caption(image_path)
        if not caption:
            db.log(image_id, "caption", "failed", "model returned empty caption")
            continue

        db.upsert_caption(image_id=image_id, caption=caption, model_name=processor.model_name)
        db.log(image_id, "caption", "success", "caption updated")
        updated += 1
        time.sleep(sleep_seconds)

    print(f"Caption updated: {updated}/{len(rows)}")
    return updated


def process_missing_colors(
    db: FashionDatabase,
    processor: GeminiFashionProcessor,
    images_dir: Optional[Path],
    limit: int,
    sleep_seconds: float,
) -> int:
    rows = db.fetch_missing_colors(limit=limit)
    if not rows:
        print("No rows with missing color.")
        return 0

    updated = 0
    for row in tqdm(rows, desc="Detecting colors"):
        image_id = row["image_id"]
        image_path = resolve_image_path(row, images_dir)
        if not image_path.exists():
            db.log(image_id, "color", "skipped", f"missing_image:{image_path}")
            continue

        color = processor.detect_item_color(image_path, row["label"])
        if not color:
            db.log(image_id, "color", "failed", "model returned empty color")
            continue

        db.upsert_color(image_id=image_id, color=color, model_name=processor.model_name)
        db.log(image_id, "color", "success", "color updated")
        updated += 1
        time.sleep(sleep_seconds)

    print(f"Color updated: {updated}/{len(rows)}")
    return updated


def load_kaggle_rows_for_upsert(
    dataset_ref: str,
    source: str,
    limit: Optional[int],
    allow_missing_images: bool,
) -> list[tuple[str, str, str, str]]:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: kagglehub. Install with `pip install kagglehub`."
        ) from exc

    print(f"Downloading Kaggle dataset: {dataset_ref}")
    cache_path = Path(kagglehub.dataset_download(dataset_ref))
    csv_path = cache_path / "images.csv"
    images_dir = cache_path / "images_compressed"

    if not csv_path.exists():
        raise RuntimeError(f"images.csv not found at {csv_path}")
    if not images_dir.exists():
        raise RuntimeError(f"images_compressed not found at {images_dir}")

    rows: list[tuple[str, str, str, str]] = []
    total = 0
    skipped_label = 0
    skipped_missing_image = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            total += 1
            image_id = (raw.get("image") or "").strip()
            label = (raw.get("label") or "").strip()
            if not image_id or not label:
                continue
            if label in EXCLUDED_LABELS:
                skipped_label += 1
                continue

            image_path = images_dir / f"{image_id}.jpg"
            if not allow_missing_images and not image_path.exists():
                skipped_missing_image += 1
                continue

            rows.append((image_id, label, str(image_path), source))
            if limit and len(rows) >= limit:
                break

    print(
        "Kaggle parse summary: "
        f"total={total}, prepared={len(rows)}, "
        f"skipped_label={skipped_label}, skipped_missing_image={skipped_missing_image}"
    )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fashion data preprocessing pipeline (PostgreSQL).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Run PostgreSQL connectivity diagnostics.")
    sub.add_parser("init-db", help="Create required tables in PostgreSQL.")

    add_item = sub.add_parser("upsert-item", help="Insert/update one fashion item row.")
    add_item.add_argument("--image-id", required=True, help="Unique item/image id.")
    add_item.add_argument("--label", required=True, help="Fashion label/category.")
    add_item.add_argument("--image-path", required=True, help="Absolute/relative image path.")
    add_item.add_argument("--source", default="manual", help="Data source identifier.")

    ingest_kaggle = sub.add_parser(
        "ingest-kaggle",
        help="Download Kaggle clothing dataset and upsert items into PostgreSQL.",
    )
    ingest_kaggle.add_argument(
        "--dataset",
        default=KAGGLE_DATASET_DEFAULT,
        help=f"Kaggle dataset reference (default: {KAGGLE_DATASET_DEFAULT}).",
    )
    ingest_kaggle.add_argument(
        "--source",
        default="kaggle",
        help="Value stored in fashion_items.source.",
    )
    ingest_kaggle.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of rows to ingest.",
    )
    ingest_kaggle.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="Ingest rows even if the local image file is missing.",
    )

    process = sub.add_parser("process", help="Generate caption/color for DB items.")
    process.add_argument(
        "--images-dir",
        default=None,
        help="Base folder for images if DB image_path is relative or empty.",
    )
    process.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of rows per run for each processing step.",
    )
    process.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between model calls (rate-limit safety).",
    )
    process.add_argument(
        "--captions",
        action="store_true",
        help="Run caption generation step.",
    )
    process.add_argument(
        "--colors",
        action="store_true",
        help="Run color detection step.",
    )
    process.add_argument(
        "--gemini-api-key",
        default=os.getenv("GEMINI_API_KEY"),
        help="Gemini API key. Defaults to GEMINI_API_KEY env var.",
    )
    process.add_argument(
        "--gemini-model",
        default=DEFAULT_GEMINI_MODEL,
        help=f"Gemini model id (default: {DEFAULT_GEMINI_MODEL}).",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = DatabaseConfig()

    if args.command == "doctor":
        sys.exit(run_doctor(config))

    env_ok, missing = validate_required_db_env(config)
    if not env_ok:
        print_missing_env_help(missing)
        sys.exit(2)

    db = FashionDatabase(config)
    try:
        db.connect()
    except psycopg2.OperationalError as exc:
        print(f"[FAIL] PostgreSQL connection failed: {exc}")
        print("  Tips:")
        print("    - Is PostgreSQL running? (docker compose up -d postgres)")
        print(f"    - Is it reachable at {config.host}:{config.port}?")
        sys.exit(1)

    try:
        if args.command == "init-db":
            db.init_tables()
            print("Database tables are ready.")
            return

        if args.command == "upsert-item":
            db.init_tables()
            db.upsert_items(
                [
                    (
                        args.image_id,
                        args.label,
                        args.image_path,
                        args.source,
                    )
                ]
            )
            print(f"Upserted item: image_id={args.image_id}")
            return

        if args.command == "ingest-kaggle":
            db.init_tables()
            rows = load_kaggle_rows_for_upsert(
                dataset_ref=args.dataset,
                source=args.source,
                limit=args.limit,
                allow_missing_images=args.allow_missing_images,
            )
            if not rows:
                print("No rows prepared for upsert.")
                return
            db.upsert_items(rows)
            print(f"Upserted {len(rows)} item(s) from dataset `{args.dataset}`.")
            return

        if args.command == "process":
            db.init_tables()
            do_captions = args.captions
            do_colors = args.colors
            if not do_captions and not do_colors:
                do_captions = True
                do_colors = True

            if not args.gemini_api_key:
                raise RuntimeError(
                    "Missing Gemini API key. Set GEMINI_API_KEY or use --gemini-api-key."
                )

            processor = GeminiFashionProcessor(
                api_key=args.gemini_api_key,
                model_name=args.gemini_model,
            )
            images_dir = Path(args.images_dir) if args.images_dir else None

            if do_colors:
                process_missing_colors(
                    db=db,
                    processor=processor,
                    images_dir=images_dir,
                    limit=args.limit,
                    sleep_seconds=args.sleep_seconds,
                )
            if do_captions:
                process_missing_captions(
                    db=db,
                    processor=processor,
                    images_dir=images_dir,
                    limit=args.limit,
                    sleep_seconds=args.sleep_seconds,
                )
            return

        raise RuntimeError(f"Unknown command: {args.command}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
