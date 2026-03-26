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


class CreateSessionResponse(BaseModel):
    session_id: str


class RatingRequest(BaseModel):
    session_id: str
    rating: int  # 1-10
    feedback: str = ""


class RatingResponse(BaseModel):
    ok: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session_endpoint(req: CreateSessionRequest):
    """Create a new chat session. Stores the user name for evaluation tracking."""
    from agent.memory import create_session
    try:
        session_id = create_session(user_name=req.user_name)
        return CreateSessionResponse(session_id=session_id)
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
    if not (1 <= req.rating <= 10):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
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
                INSERT INTO user_ratings (session_id, user_name, rating, feedback)
                VALUES (%s, %s, %s, %s);
                """,
                (req.session_id, user_name, req.rating, req.feedback),
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
                SELECT user_name, rating, feedback, created_at
                FROM user_ratings
                ORDER BY rating DESC, created_at DESC;
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
            }
            for r in rows
        ]
        return {"entries": entries, "count": len(entries)}
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
        reload=False,
        log_level="info",
    )
