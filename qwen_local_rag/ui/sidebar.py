# =============================================================================
# ui/sidebar.py — Toàn bộ cấu hình sidebar Streamlit
# Tách riêng để app.py gọn hơn, dễ thêm/bớt tuỳ chọn sidebar
# =============================================================================

import streamlit as st
from config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    MODEL_HELP,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SEARCH_DOMAINS,
)


def init_session_state():
    """
    Khởi tạo toàn bộ session state với giá trị mặc định.
    Gọi 1 lần duy nhất ở đầu app.py.
    """
    defaults = {
        "model_version": DEFAULT_MODEL,
        "vector_store": None,
        "processed_documents": [],
        "history": [],
        "exa_api_key": "",
        "use_web_search": False,
        "force_web_search": False,
        "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD,
        "rag_enabled": True,
        "search_domains": DEFAULT_SEARCH_DOMAINS,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """
    Render toàn bộ sidebar và cập nhật session_state.
    Hàm này không trả về gì — mọi thứ được ghi vào st.session_state.
    """
    st.sidebar.header("⚙️ Cài đặt")

    # ── Model Selection ──────────────────────────────────────────────────────
    st.sidebar.header("🧠 Chọn Model")
    st.session_state.model_version = st.sidebar.radio(
        "Model Version",
        options=AVAILABLE_MODELS,
        help=MODEL_HELP,
    )
    st.sidebar.info("Chạy: `ollama pull qwen3:1.7b` để tải model")

    # ── RAG Toggle ───────────────────────────────────────────────────────────
    st.sidebar.header("📚 RAG Mode")
    st.session_state.rag_enabled = st.sidebar.toggle(
        "Bật RAG",
        value=st.session_state.rag_enabled,
    )

    # ── Clear Chat ───────────────────────────────────────────────────────────
    if st.sidebar.button("✨ Xoá Chat"):
        st.session_state.history = []
        st.rerun()

    # ── Search Tuning (chỉ khi RAG bật) ─────────────────────────────────────
    if st.session_state.rag_enabled:
        st.sidebar.header("🔬 Tuning Tìm Kiếm")
        st.session_state.similarity_threshold = st.sidebar.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.similarity_threshold,
            help="Thấp hơn = nhiều kết quả hơn nhưng kém chính xác hơn.",
        )

    # ── Web Search ───────────────────────────────────────────────────────────
    st.sidebar.header("🌍 Web Search")
    st.session_state.use_web_search = st.sidebar.checkbox(
        "Bật Web Search Fallback",
        value=st.session_state.use_web_search,
    )

    if st.session_state.use_web_search:
        exa_key = st.sidebar.text_input(
            "Exa AI API Key",
            type="password",
            value=st.session_state.exa_api_key,
            help="Cần để fallback sang web search khi không tìm thấy tài liệu",
        )
        st.session_state.exa_api_key = exa_key

        custom_domains = st.sidebar.text_input(
            "Custom domains (phân cách bằng dấu phẩy)",
            value=",".join(st.session_state.search_domains),
            help="Ví dụ: arxiv.org,wikipedia.org",
        )
        st.session_state.search_domains = [
            d.strip() for d in custom_domains.split(",") if d.strip()
        ]

    # ── Processed Sources ─────────────────────────────────────────────────────
    if st.session_state.processed_documents:
        st.sidebar.header("📚 Nguồn đã xử lý")
        for source in st.session_state.processed_documents:
            icon = "📄" if source.endswith(".pdf") else "🌐"
            st.sidebar.text(f"{icon} {source}")