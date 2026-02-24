# =============================================================================
# core/agents.py — Khởi tạo các Agno Agent: RAG Agent và Web Search Agent
# Tách riêng để dễ thêm agent mới (image agent, code agent…) hoặc đổi provider
# =============================================================================

import streamlit as st
from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.exa import ExaTools

from config import WEB_SEARCH_MODEL, WEB_SEARCH_NUM_RESULTS


def get_rag_agent(model_version: str = None) -> Agent:
    """
    Khởi tạo RAG Agent chính với model Ollama được chọn từ sidebar.

    Args:
        model_version: ID của model Ollama (ví dụ: "qwen3:1.7b").

    Returns:
        Agent đã cấu hình sẵn.
    """
    model_id = model_version or st.session_state.get("model_version", "qwen3:1.7b")

    return Agent(
        name="Qwen 3 RAG Agent",
        model=Ollama(id=model_id),
        instructions="""Bạn là một AI Agent thông minh, chuyên trả lời chính xác và rõ ràng.

Khi nhận câu hỏi thuần túy (không có context):
- Trả lời dựa trên kiến thức của bạn.

Khi được cung cấp context từ documents:
- Tập trung vào thông tin trong documents.
- Trích dẫn cụ thể từ nguồn tài liệu.

Khi được cung cấp kết quả web search:
- Nêu rõ thông tin đến từ web search.
- Tổng hợp thông tin súc tích và rõ ràng.

Luôn duy trì độ chính xác cao và trình bày dễ hiểu.
""",
        debug_mode=True,
        markdown=True,
    )


def get_web_search_agent(
    api_key: str,
    search_domains: list,
) -> Agent:
    """
    Khởi tạo Web Search Agent dùng Exa AI.

    Args:
        api_key: Exa AI API key.
        search_domains: Danh sách domain được phép tìm kiếm.

    Returns:
        Agent đã cấu hình với ExaTools.
    """
    return Agent(
        name="Web Search Agent",
        model=Ollama(id=WEB_SEARCH_MODEL),
        tools=[
            ExaTools(
                api_key=api_key,
                include_domains=search_domains,
                num_results=WEB_SEARCH_NUM_RESULTS,
            )
        ],
        instructions="""Bạn là chuyên gia tìm kiếm web. Nhiệm vụ của bạn:
1. Tìm kiếm thông tin liên quan đến câu hỏi.
2. Tổng hợp và tóm tắt thông tin quan trọng nhất.
3. Luôn kèm nguồn (source) trong câu trả lời.
""",
        debug_mode=True,
        markdown=True,
    )