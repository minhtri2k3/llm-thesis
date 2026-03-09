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
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agent.fashion_agent import chat as agent_chat, AgentResponse
from agent.memory import init_memory_tables

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "images"))
DATASET_IMAGES_DIR = Path(os.getenv("DATASET_IMAGES_DIR", "/app/dataset_images"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))


def _convert_image_path(host_path: str) -> Optional[Path]:
    """Convert host absolute image path to container path.

    Extracts the basename (e.g. 'ea7b6656.jpg') and maps to
    /app/dataset_images/ea7b6656.jpg. Returns None if file doesn't exist.
    """
    if not host_path:
        return None
    filename = os.path.basename(host_path)
    container_path = DATASET_IMAGES_DIR / filename
    if container_path.exists():
        return container_path
    return None

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Main agent chat endpoint."""
    try:
        result: AgentResponse = agent_chat(
            query=req.message,
            session_id=req.session_id,
        )
        return ChatResponse(
            answer=result.answer,
            products=[
                {
                    "image_id": p.image_id,
                    "image_path": p.image_path,
                    "label": p.label,
                    "color": p.color,
                    "caption": p.caption,
                    "score": p.score,
                }
                for p in result.products
            ],
            styling_suggestion=result.styling_suggestion,
            reasoning=result.reasoning,
            session_id=result.session_id,
            intent=result.intent,
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
    """Serve product images."""
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

    def respond(message: str, history: list, session_id_state: str):
        result = agent_chat(
            query=message,
            session_id=session_id_state if session_id_state else None,
        )

        # Build list of assistant messages (text + optional images)
        messages: list[dict] = []

        # 1. Text response
        text_response = result.answer
        if result.styling_suggestion:
            text_response += f"\n\n💡 **Styling tip:** {result.styling_suggestion}"

        if result.products:
            text_response += "\n\n---\n### 🛍️ Sản phẩm tìm thấy:\n"
            for i, p in enumerate(result.products, 1):
                text_response += f"\n**{i}. {p.label}** — {p.color}\n"
                if p.caption:
                    cap = p.caption[:100] + "..." if len(p.caption) > 100 else p.caption
                    text_response += f"   _{cap}_\n"

        messages.append({"role": "assistant", "content": text_response})

        # 2. Product images (graceful degradation: skip if file not found)
        if result.products:
            for p in result.products:
                img_path = _convert_image_path(p.image_path)
                if img_path is not None:
                    alt = f"{p.label} — {p.color}" if p.color else p.label
                    messages.append({
                        "role": "assistant",
                        "content": {"path": str(img_path), "alt_text": alt},
                    })

        new_session_id = result.session_id
        return messages, new_session_id

    with gr.Blocks(
        title="🛍️ Fashion Agent",
    ) as demo:
        gr.Markdown("# 🛍️ Fashion Agent\n*Trợ lý tìm kiếm thời trang thông minh*")

        session_id_state = gr.State("")

        chatbot = gr.Chatbot(
            label="Fashion Agent Chat",
            height=500,
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
                return "", history, session_id_state

            assistant_msgs, new_session_id = respond(message, history, session_id_state)
            # Add user message
            history = history + [{"role": "user", "content": message}]
            # Add all assistant messages (text + images)
            history = history + assistant_msgs
            return "", history, new_session_id

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
