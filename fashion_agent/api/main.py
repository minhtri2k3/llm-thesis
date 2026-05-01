"""
Fashion Agent RAG Pipeline — FastAPI + Gradio API.

Endpoints:
    POST /api/chat              — Agent chat (search/recommend/chat)
    GET  /api/products/{id}     — Get product by image_id
    GET  /api/images/{filename} — Serve product image
    GET  /health                — Health check
    /                           — Gradio UI (mounted at root)
"""

from __future__ import annotations

import datetime
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent.fashion_agent import chat as agent_chat, chat_stream as agent_chat_stream, AgentResponse
from agent.memory import init_memory_tables

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "images"))
DATASET_IMAGES_DIR = Path(os.getenv("DATASET_IMAGES_DIR", "/app/dataset_images"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize resources on startup."""
    try:
        init_memory_tables()
        print("Memory tables initialized.")
    except Exception as exc:
        print(f"Warning: Could not initialize memory tables: {exc}")
    yield


app = FastAPI(
    title="Fashion Agent RAG API",
    description="Hybrid RAG fashion search agent with Marqo-FashionSigLIP, BGE Reranker, and Gemini synthesis.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    products: list[dict] = []
    styling_suggestion: str = ""
    reasoning: str = ""
    session_id: str = ""
    intent: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict


class CreateSessionRequest(BaseModel):
    user_name: str = ""
    year_of_birth: Optional[int] = None
    gender: Optional[str] = None
    preferred_model: str = "gemini-2.5-flash"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    def model_post_init(self, __context) -> None:  # noqa: D401
        current_year = datetime.date.today().year
        if self.year_of_birth is not None:
            if not (1900 <= self.year_of_birth <= current_year):
                raise ValueError(
                    f"year_of_birth must be between 1900 and {current_year}"
                )
        if self.gender is not None and self.gender not in ("male", "female"):
            raise ValueError('gender must be "male" or "female"')
        if self.preferred_model not in ("gemini-2.5-flash", "gpt-4o", "claude-3-7-sonnet-latest"):
            raise ValueError('preferred_model must be one of: gemini-2.5-flash, gpt-4o, claude-3-7-sonnet-latest')


class CreateSessionResponse(BaseModel):
    session_id: str


class RatingRequest(BaseModel):
    session_id: str
    rating_overall: int        # 1–5: overall experience
    rating_suggestions: int    # 1–5: were suggestions right?
    rating_conversation: int   # 1–5: how natural was the conversation?
    feedback: str = ""


class RatingResponse(BaseModel):
    ok: bool


class DemographicsGenderEntry(BaseModel):
    gender: str
    avg_rating: float
    count: int


class DemographicsAgeEntry(BaseModel):
    age_group: str
    avg_rating: float
    count: int


class DemographicsResponse(BaseModel):
    by_gender: list[DemographicsGenderEntry] = []
    by_age_group: list[DemographicsAgeEntry] = []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session_endpoint(req: CreateSessionRequest):
    """Create a new chat session. Stores the user name and demographics for evaluation tracking."""
    from agent.memory import create_session
    try:
        session_id = create_session(
            user_name=req.user_name,
            year_of_birth=req.year_of_birth,
            gender=req.gender,
            preferred_model=req.preferred_model,
        )
        return CreateSessionResponse(session_id=session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/sessions/{session_id}/selections/{image_id}")
async def remove_cart_item(session_id: str, image_id: str):
    """Remove a selected item from the cart log."""
    from agent.memory import log_cart_removal
    try:
        success = log_cart_removal(session_id, image_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cart item not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/sessions/{session_id}/selections")
async def get_session_selections(session_id: str):
    """Return all confirmed product selections for a given session."""
    from agent.memory import get_selected_items
    import os
    try:
        items = get_selected_items(session_id)
        # Transform image_path (full disk path) → filename only so the
        # client can build a portable URL: /api/images/<filename>
        for item in items:
            raw = item.get("image_path", "")
            item["image_path"] = os.path.basename(raw) if raw else ""
        return {"session_id": session_id, "items": items, "count": len(items)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/rating", response_model=RatingResponse)
async def submit_rating_endpoint(req: RatingRequest):
    """Submit a post-session rating and feedback for thesis evaluation."""
    for field_name, val in [
        ("rating_overall", req.rating_overall),
        ("rating_suggestions", req.rating_suggestions),
        ("rating_conversation", req.rating_conversation),
    ]:
        if not (1 <= val <= 5):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} must be between 1 and 5",
            )
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            # Get user_name from session for denormalized storage
            cur.execute(
                "SELECT user_name FROM user_sessions WHERE session_id = %s;",
                (req.session_id,),
            )
            row = cur.fetchone()
            user_name = row[0] if row else ""
            cur.execute(
                """
                INSERT INTO user_ratings
                    (session_id, user_name, rating,
                     rating_overall, rating_suggestions, rating_conversation,
                     feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    req.session_id,
                    user_name,
                    req.rating_overall * 2,      # backward-compat: 5→10, 4→8…
                    req.rating_overall,
                    req.rating_suggestions,
                    req.rating_conversation,
                    req.feedback,
                ),
            )
        conn.commit()
        conn.close()
        return RatingResponse(ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ratings")
async def get_ratings_endpoint():
    """Return all session ratings ordered by rating desc — used for leaderboard."""
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT r.user_name, r.rating, r.feedback, r.created_at,
                       s.year_of_birth, s.gender,
                       sts.model_name, sts.total_tokens
                FROM user_ratings r
                JOIN user_sessions s ON s.session_id = r.session_id
                LEFT JOIN session_token_summary sts ON sts.session_id = r.session_id
                ORDER BY r.rating DESC, r.created_at DESC;
                """
            )
            rows = cur.fetchall()
        conn.close()
        entries = [
            {
                "user_name": r["user_name"] or "Anonymous",
                "rating": r["rating"],
                "feedback": r["feedback"],
                "rated_at": str(r["created_at"]),
                "year_of_birth": r["year_of_birth"],
                "gender": r["gender"],
                "model_name": r["model_name"] or "gemini-2.5-flash",
                "total_tokens": r["total_tokens"] or 0,
            }
            for r in rows
        ]
        return {"entries": entries, "count": len(entries)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/demographics", response_model=DemographicsResponse)
async def get_demographics_endpoint(request: Request):
    """Return demographic breakdown of ratings — avg. by gender and by age group.

    Protected by X-Admin-Key header.
    Only sessions with both year_of_birth and gender are included.
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key:
        raise HTTPException(status_code=503, detail="Analytics not configured")

    provided_key = request.headers.get("X-Admin-Key", "")
    if provided_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # By gender
            cur.execute(
                """
                SELECT s.gender,
                       ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                       COUNT(*) AS count
                FROM user_ratings r
                JOIN user_sessions s ON s.session_id = r.session_id
                WHERE s.gender IS NOT NULL
                GROUP BY s.gender
                ORDER BY s.gender;
                """
            )
            gender_rows = cur.fetchall()

            # By age group
            cur.execute(
                """
                SELECT
                    CASE
                        WHEN EXTRACT(YEAR FROM s.created_at) - s.year_of_birth < 20 THEN 'Under 20'
                        WHEN EXTRACT(YEAR FROM s.created_at) - s.year_of_birth < 30 THEN '20-29'
                        WHEN EXTRACT(YEAR FROM s.created_at) - s.year_of_birth < 40 THEN '30-39'
                        ELSE '40+'
                    END AS age_group,
                    ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                    COUNT(*) AS count
                FROM user_ratings r
                JOIN user_sessions s ON s.session_id = r.session_id
                WHERE s.year_of_birth IS NOT NULL
                GROUP BY age_group
                ORDER BY MIN(EXTRACT(YEAR FROM s.created_at) - s.year_of_birth);
                """
            )
            age_rows = cur.fetchall()
        conn.close()

        return DemographicsResponse(
            by_gender=[
                DemographicsGenderEntry(
                    gender=r["gender"],
                    avg_rating=float(r["avg_rating"]),
                    count=r["count"],
                )
                for r in gender_rows
            ],
            by_age_group=[
                DemographicsAgeEntry(
                    age_group=r["age_group"],
                    avg_rating=float(r["avg_rating"]),
                    count=r["count"],
                )
                for r in age_rows
            ],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/analytics/token-usage")
async def get_token_usage_analytics(request: Request):
    """Return per-session LLM token usage — protected by ADMIN_SECRET_KEY.

    Requires header: X-Admin-Key: <value of ADMIN_SECRET_KEY env var>

    Responses:
    - 200: {"sessions": [...], "total_sessions": N, "grand_total_tokens": M}
    - 403: Forbidden (wrong or missing key)
    - 503: Analytics not configured (env var not set)
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key:
        raise HTTPException(status_code=503, detail="Analytics not configured")

    provided_key = request.headers.get("X-Admin-Key", "")
    if provided_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        from agent.memory import get_token_analytics
        sessions = get_token_analytics()
        grand_total = sum(s["total_tokens"] for s in sessions)
        return {
            "sessions": sessions,
            "total_sessions": len(sessions),
            "grand_total_tokens": grand_total,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Thesis evaluation analytics (token costs, accuracy, gender A/B)
# ---------------------------------------------------------------------------

from api.analytics import get_token_costs, get_accuracy, get_gender_ab

app.add_api_route("/api/analytics/token-costs", get_token_costs, methods=["GET"])
app.add_api_route("/api/analytics/accuracy",    get_accuracy,    methods=["GET"])
app.add_api_route("/api/analytics/gender-ab",    get_gender_ab,   methods=["GET"])


# ---------------------------------------------------------------------------
# Behaviour tracking — Pydantic models (Task 3)
# ---------------------------------------------------------------------------


class ImpressionItem(BaseModel):
    image_id: str
    search_query: str = ""
    position: int = 0


class LogImpressionsRequest(BaseModel):
    items: list[ImpressionItem]


class ClickRequest(BaseModel):
    image_id: str
    position: int = 0
    search_query: str = ""


class IntentRequest(BaseModel):
    image_id: str
    intent_type: str   # "will_buy" | "not_for_me"
    reason: str = ""


class OrderRequest(BaseModel):
    phone: str
    address: str


# ---------------------------------------------------------------------------
# Behaviour tracking — Endpoints (Tasks 4-8)
# ---------------------------------------------------------------------------


@app.post("/api/sessions/{session_id}/impressions")
async def log_impressions_endpoint(session_id: str, req: LogImpressionsRequest):
    """Batch-log product impressions for a search result. Fire-and-forget safe."""
    from agent.memory import log_impression_batch
    try:
        logged = log_impression_batch(
            session_id,
            [
                {
                    "image_id": i.image_id,
                    "search_query": i.search_query,
                    "position": i.position,
                }
                for i in req.items
            ],
        )
        return {"ok": True, "logged": logged}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sessions/{session_id}/clicks")
async def log_click_endpoint(session_id: str, req: ClickRequest):
    """Log a product card tap (click event). Fire-and-forget safe."""
    from agent.memory import log_click
    try:
        log_click(
            session_id,
            req.image_id,
            req.position,
            req.search_query,
        )
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sessions/{session_id}/intents")
async def log_intent_endpoint(session_id: str, req: IntentRequest):
    """Log a purchase intent signal (will_buy | not_for_me)."""
    if req.intent_type not in ("will_buy", "not_for_me"):
        raise HTTPException(
            status_code=400,
            detail="intent_type must be 'will_buy' or 'not_for_me'",
        )
    from agent.memory import log_intent
    try:
        log_intent(session_id, req.image_id, req.intent_type, req.reason)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sessions/{session_id}/orders")
async def place_order_endpoint(session_id: str, req: OrderRequest):
    """Save a simulated order and mark the session as ended (conversion event).

    This is the primary signal for Conversion Rate (CR) analytics.
    Atomically creates the order row and sets ended_at / ended_by on the session.
    """
    if not req.phone.strip():
        raise HTTPException(status_code=400, detail="phone is required")
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="address is required")
    from agent.memory import save_order
    try:
        order_id = save_order(session_id, req.phone.strip(), req.address.strip())
        return {"ok": True, "order_id": order_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/analytics/behaviour-funnel")
async def get_behaviour_funnel_endpoint(request: Request):
    """Full funnel analytics: per-session metrics + model comparison table.

    Protected by X-Admin-Key header (same ADMIN_SECRET_KEY env var).

    Returns:
        sessions:          list of per-session funnel dicts
        model_comparison:  aggregate stats grouped by LLM model
        aggregate:         overall totals (total_sessions, cr, avg_precision_at_k)
    """
    from collections import defaultdict
    from agent.memory import get_session_funnel

    admin_key = os.getenv("ADMIN_SECRET_KEY", "")
    if not admin_key:
        raise HTTPException(
            status_code=503,
            detail="Analytics not configured (ADMIN_SECRET_KEY missing)",
        )
    if request.headers.get("X-Admin-Key", "") != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        import psycopg2
        from psycopg2.extras import DictCursor

        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT s.session_id, s.user_name, s.gender,
                       DATE_PART('year', NOW()) - s.year_of_birth AS age
                FROM user_sessions s
                ORDER BY s.created_at DESC
                LIMIT 500;
                """
            )
            session_rows = cur.fetchall()
        conn.close()

        # Build per-session funnel data
        sessions = []
        for row in session_rows:
            funnel = get_session_funnel(row["session_id"])
            funnel["user_name"] = row["user_name"]
            funnel["gender"] = row["gender"]
            funnel["age"] = int(row["age"]) if row["age"] else None
            sessions.append(funnel)

        # Model comparison aggregate
        model_groups: dict = defaultdict(lambda: {
            "sessions": 0,
            "orders": 0,
            "total_tokens": 0,
            "precision_sum": 0.0,
        })
        for s in sessions:
            model = s["model_name"] or "unknown"
            model_groups[model]["sessions"] += 1
            if s["converted"]:
                model_groups[model]["orders"] += 1
            model_groups[model]["total_tokens"] += s["total_tokens"] or 0
            model_groups[model]["precision_sum"] += s["precision_at_k"]

        model_comparison = []
        for model, g in model_groups.items():
            n = g["sessions"]
            model_comparison.append({
                "model": model,
                "sessions": n,
                "orders": g["orders"],
                "conversion_rate": round(g["orders"] / n, 3) if n else 0.0,
                "avg_precision_at_k": round(g["precision_sum"] / n, 3) if n else 0.0,
                "avg_tokens": round(g["total_tokens"] / n) if n else 0,
            })
        model_comparison.sort(key=lambda x: -x["conversion_rate"])

        total = len(sessions)
        converted = sum(1 for s in sessions if s["converted"])

        return {
            "sessions": sessions,
            "model_comparison": model_comparison,
            "aggregate": {
                "total_sessions": total,
                "converted_sessions": converted,
                "overall_cr": round(converted / total, 3) if total else 0.0,
                "avg_precision_at_k": round(
                    sum(s["precision_at_k"] for s in sessions) / total, 3
                ) if total else 0.0,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """Streaming chat endpoint — returns Server-Sent Events.

    Event types:
    - token: text chunks as they arrive from Gemini
    - clarification: clarification question (non-streamed)
    - products: list of matching products
    - done: final metadata (session_id, intent, styling)
    """
    try:
        return StreamingResponse(
            agent_chat_stream(
                query=req.message,
                session_id=req.session_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/products/{image_id}")
async def get_product(image_id: str):
    """Get product details by image_id."""
    import psycopg2
    from psycopg2.extras import DictCursor

    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=5,
        )
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT fi.*, fe.caption, fe.color
                FROM fashion_items fi
                LEFT JOIN fashion_item_enrichment fe ON fe.image_id = fi.image_id
                WHERE fi.image_id = %s;
                """,
                (image_id,),
            )
            row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/images/{filename:path}")
async def serve_image(filename: str):
    """Serve product images from dataset or local images directory."""
    # Try dataset images_compressed subfolder first (mounted from Kaggle dataset)
    file_path = DATASET_IMAGES_DIR / "images_compressed" / filename
    if not file_path.exists():
        # Try root dataset_images directory
        file_path = DATASET_IMAGES_DIR / filename
    if not file_path.exists():
        # Fallback to local images directory
        file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    return FileResponse(str(file_path))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {}

    # Check PostgreSQL
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "fashion_rag"),
            user=os.getenv("PGUSER", "fashion_user"),
            password=os.getenv("PGPASSWORD", ""),
            connect_timeout=3,
        )
        conn.close()
        services["postgresql"] = "healthy"
    except Exception:
        services["postgresql"] = "unhealthy"

    # Check Qdrant
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            timeout=3,
            https=False,  # Use HTTP for local Docker connection
            prefer_grpc=False,
        )
        client.get_collections()
        services["qdrant"] = "healthy"
    except Exception:
        services["qdrant"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        services=services,
    )


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def create_gradio_app():
    """Create the Gradio chat interface."""
    try:
        import gradio as gr
    except ImportError:
        print("Gradio not installed — UI will not be available.")
        return None

    css = """
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 12px;
        margin: 8px 4px;
        background: #fafafa;
    }
    .product-card img {
        border-radius: 8px;
        max-height: 200px;
        object-fit: cover;
    }
    """

    def _parse_single_sse(event_str: str) -> tuple[str, dict]:
        """Parse one SSE event string into (event_type, data_dict).

        Returns ("", {}) if parsing fails.
        """
        import json as _json
        event_type = ""
        data_str = ""
        for line in event_str.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
        if event_type and data_str:
            try:
                return event_type, _json.loads(data_str)
            except _json.JSONDecodeError:
                pass
        return "", {}

    def _format_product_cards(product_data: list) -> str:
        """Format product data into markdown text with markdown images."""
        if not product_data:
            return ""

        text = "\n\n---\n### 🛍️ Sản phẩm tìm thấy:\n\n"
        for i, p in enumerate(product_data, 1):
            label = p.get("label", "")
            if not label or not label.strip():
                continue

            color = p.get("color", "")
            color_str = f" — {color}" if color and color.strip() else ""
            text += f"**{i}. {label}**{color_str}\n"

            caption = p.get("caption", "")
            if caption and caption.strip():
                cap = caption
                text += f"_{cap}_\n"

            # Use markdown image syntax (Gradio 6.x compatible)
            img_path = p.get("image_path", "")
            if img_path:
                filename = os.path.basename(img_path)
                text += f"\n![{label}](/api/images/{filename})\n\n"
            else:
                text += "\n"

        return text

    def respond_stream(message: str, history: list, session_id_state: str):
        """True streaming handler — yields progressive chatbot updates.

        Handles thinking events (collapsible block), model thinking,
        response tokens, products, and styling.
        """
        sid = session_id_state if session_id_state else None
        accumulated_text = ""
        new_session_id = session_id_state
        product_cards = ""
        styling = ""

        # Thinking state
        thinking_steps: list[str] = []
        model_thinking_parts: list[str] = []
        thinking_active = False
        thinking_duration_ms = 0
        thinking_block = ""
        total_in = 0
        total_out = 0

        for event_str in agent_chat_stream(query=message, session_id=sid):
            etype, edata = _parse_single_sse(event_str)
            if not etype:
                continue

            if etype == "thinking_start":
                thinking_active = True
                thinking_steps.clear()
                # Show live thinking indicator
                accumulated_text = "🤔 **Đang suy nghĩ...**\n"
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "thinking_step":
                detail = edata.get("detail", "")
                thinking_steps.append(f"✓ {detail}")
                # Update with progressive thinking steps
                steps_text = "\n".join(thinking_steps)
                accumulated_text = f"🤔 **Đang suy nghĩ...**\n{steps_text}\n"
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "thinking_end":
                thinking_active = False
                thinking_duration_ms = edata.get("duration_ms", 0)
                duration_sec = thinking_duration_ms / 1000
                steps_text = "\n".join(thinking_steps)

                # Build token info string for header
                t_in = edata.get("input_tokens", 0)
                t_out = edata.get("output_tokens", 0)
                token_str = f" — 📊 {t_in} in / {t_out} out" if (t_in or t_out) else ""

                # Wrap in collapsible <details> block
                thinking_block = (
                    f"<details>\n"
                    f"<summary>🤔 Đã suy nghĩ ({duration_sec:.1f}s){token_str}</summary>\n\n"
                    f"{steps_text}\n\n"
                    f"</details>\n\n"
                )
                accumulated_text = thinking_block
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "model_thinking":
                model_thinking_parts.append(edata.get("text", ""))

            elif etype == "token":
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "clarification":
                # Clarification comes after thinking_end
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "products":
                product_cards = _format_product_cards(edata.get("products", []))

            elif etype == "selection_confirm":
                # Product selection confirmation preview
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "selection_saved":
                # Product selection saved successfully
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "selection_cancelled":
                # Product selection cancelled
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "selections_list":
                # View all selections
                accumulated_text += edata.get("text", "")
                yield (
                    history + [{"role": "assistant", "content": accumulated_text}],
                    new_session_id,
                )

            elif etype == "done":
                new_session_id = edata.get("session_id", session_id_state)
                styling = edata.get("styling", "")
                # Capture total token counts for final render
                total_in = edata.get("total_input_tokens", 0)
                total_out = edata.get("total_output_tokens", 0)

        # Final yield with styling + products + model thinking appended
        final_text = accumulated_text

        # Append model thinking as collapsible if present
        if model_thinking_parts:
            model_think_text = "".join(model_thinking_parts)
            if len(model_think_text) > 500:
                model_think_text = model_think_text[:500] + "..."
            final_text += (
                f"\n\n<details>\n"
                f"<summary>💭 Model reasoning</summary>\n\n"
                f"{model_think_text}\n\n"
                f"</details>"
            )

        if styling:
            final_text += f"\n\n💡 **Styling tip:** {styling}"
        if product_cards:
            final_text += product_cards

        # Append total token usage footer
        if total_in or total_out:
            total = total_in + total_out
            final_text += f"\n\n📊 Total: {total_in} in / {total_out} out ({total} tokens)"

        yield (
            history + [{"role": "assistant", "content": final_text}],
            new_session_id,
        )

    with gr.Blocks(
        title="🛍️ Fashion Agent",
    ) as demo:
        gr.Markdown("# 🛍️ Fashion Agent\n*Trợ lý tìm kiếm thời trang thông minh*")

        session_id_state = gr.State("")

        chatbot = gr.Chatbot(
            label="Fashion Agent Chat",
            height=600,
        )

        msg = gr.Textbox(
            label="Tin nhắn",
            placeholder="Tìm áo sơ mi trắng cho đi làm...",
            scale=7,
        )

        with gr.Row():
            submit_btn = gr.Button("Gửi 🚀", variant="primary", scale=1)
            clear_btn = gr.Button("Xóa chat 🗑️", scale=1)

        def user_submit(message, history, session_id_state):
            if not message.strip():
                yield "", history, session_id_state
                return

            # Add user message immediately
            updated_history = history + [{"role": "user", "content": message}]
            yield "", updated_history, session_id_state

            # Stream assistant response
            for streamed_history, new_sid in respond_stream(message, updated_history, session_id_state):
                yield "", streamed_history, new_sid

        def clear_chat():
            return [], ""

        msg.submit(
            user_submit,
            [msg, chatbot, session_id_state],
            [msg, chatbot, session_id_state],
        )
        submit_btn.click(
            user_submit,
            [msg, chatbot, session_id_state],
            [msg, chatbot, session_id_state],
        )
        clear_btn.click(
            clear_chat,
            outputs=[chatbot, session_id_state],
        )

    return demo


# ---------------------------------------------------------------------------
# Mount Gradio
# ---------------------------------------------------------------------------

gradio_app = create_gradio_app()
if gradio_app is not None:
    from gradio import mount_gradio_app

    app = mount_gradio_app(app, gradio_app, path="/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )
