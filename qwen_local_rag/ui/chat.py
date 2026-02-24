# =============================================================================
# ui/chat.py — Toàn bộ logic chat: document upload, RAG flow, simple mode
# Mỗi hàm đảm nhận 1 trách nhiệm rõ ràng → dễ test và sửa đổi
# =============================================================================

import re
from typing import Optional, List

import streamlit as st

from core.agents import get_rag_agent, get_web_search_agent

from core.vector_store import create_vector_store, retrieve_documents, init_cloud_sql
from loaders.pdf_loader import process_pdf
from loaders.web_loader import process_web



# ─────────────────────────────────────────────────────────────────────────────
# Document Upload Section
# ─────────────────────────────────────────────────────────────────────────────

def render_document_upload():
    """
    Render phần upload PDF / URL trong expander.
    Chỉ hiển thị khi RAG mode đang bật.
    """
    cloud_sql_engine = init_cloud_sql()

    with st.expander("📁 Upload Documents hoặc URL cho RAG", expanded=False):
        if not cloud_sql_engine:
            st.warning("⚠️ Không kết nối được Cloud SQL. Kiểm tra proxy đang chạy.")
            return

        uploaded_files = st.file_uploader(
            "Upload file PDF",
            accept_multiple_files=True,
            type="pdf",
        )
        url_input = st.text_input("Nhập URL để scrape")

        all_texts = []

        # Xử lý PDF
        if uploaded_files:
            st.write(f"Đang xử lý {len(uploaded_files)} file PDF...")
            for file in uploaded_files:
                if file.name not in st.session_state.processed_documents:
                    with st.spinner(f"Đang xử lý {file.name}..."):
                        texts = process_pdf(file)
                        if texts:
                            all_texts.extend(texts)
                            st.session_state.processed_documents.append(file.name)
                else:
                    st.write(f"📄 {file.name} đã được xử lý trước đó.")

        # Xử lý URL
        if url_input:
            if url_input not in st.session_state.processed_documents:
                with st.spinner(f"Đang scrape {url_input}..."):
                    texts = process_web(url_input)
                    if texts:
                        all_texts.extend(texts)
                        st.session_state.processed_documents.append(url_input)
            else:
                st.write(f"🔗 {url_input} đã được xử lý trước đó.")

        # Tạo vector store nếu có tài liệu mới
        if all_texts:
            with st.spinner("Đang tạo vector store..."):
                st.session_state.vector_store = create_vector_store(
                    cloud_sql_engine, all_texts
                )

        if st.session_state.vector_store:
            st.success("Vector store đã sẵn sàng.")
        elif not uploaded_files and not url_input:
            st.info("Upload PDF hoặc nhập URL để bắt đầu RAG.")


# ─────────────────────────────────────────────────────────────────────────────
# Context Retrieval Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_rag_context(query: str) -> tuple[str, List]:
    """
    Tìm context từ vector store, fallback sang web search nếu cần.

    Returns:
        (context_string, docs_list)
    """
    context = ""
    docs = []

    # Thử vector store trước (nếu không force web search)
    if not st.session_state.force_web_search and st.session_state.vector_store:
        docs = retrieve_documents(
            st.session_state.vector_store,
            query,
            threshold=st.session_state.similarity_threshold,
        )
        if docs:
            context = "\n\n".join([d.page_content for d in docs])
            st.info(
                f"📊 Tìm thấy {len(docs)} tài liệu liên quan "
                f"(similarity > {st.session_state.similarity_threshold})"
            )
        elif st.session_state.use_web_search:
            st.info("🔄 Không tìm thấy tài liệu phù hợp, fallback sang web search...")

    # Web search nếu: force ON hoặc không có context từ docs
    need_web = st.session_state.force_web_search or not context
    if need_web and st.session_state.use_web_search and st.session_state.exa_api_key:
        with st.spinner("🔍 Đang tìm kiếm web..."):
            try:
                agent = get_web_search_agent(
                    api_key=st.session_state.exa_api_key,
                    search_domains=st.session_state.search_domains,
                )
                web_results = agent.run(query).content
                if web_results:
                    context = f"Web Search Results:\n{web_results}"
                    label = "theo yêu cầu" if st.session_state.force_web_search else "fallback"
                    st.info(f"ℹ️ Đang dùng web search ({label}).")
            except Exception as e:
                st.error(f"❌ Web search error: {str(e)}")

    return context, docs


def _build_prompt(query: str, context: str) -> str:
    """Ghép context và câu hỏi thành prompt đầy đủ."""
    if context:
        return (
            f"Context:\n{context}\n\n"
            f"Câu hỏi gốc: {query}\n"
            "Hãy trả lời dựa trên thông tin có sẵn."
        )
    return query


def _extract_thinking(response_content: str) -> tuple[Optional[str], str]:
    """
    Tách phần <think>...</think> (chain-of-thought) khỏi câu trả lời chính.

    Returns:
        (thinking_text | None, final_response)
    """
    pattern = r"<think>(.*?)</think>"
    match = re.search(pattern, response_content, re.DOTALL)
    if match:
        thinking = match.group(1).strip()
        final = re.sub(pattern, "", response_content, flags=re.DOTALL).strip()
        return thinking, final
    return None, response_content


# ─────────────────────────────────────────────────────────────────────────────
# Chat Display
# ─────────────────────────────────────────────────────────────────────────────

def render_chat_history():
    """Hiển thị lại toàn bộ lịch sử chat."""
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_chat_input():
    """
    Render chat input bar + nút toggle web search.
    Trả về (prompt, force_web_search).
    """
    chat_col, toggle_col = st.columns([0.9, 0.1])
    with chat_col:
        placeholder = (
            "Hỏi về tài liệu của bạn..."
            if st.session_state.rag_enabled
            else "Hỏi tôi bất cứ điều gì..."
        )
        prompt = st.chat_input(placeholder)
    with toggle_col:
        st.session_state.force_web_search = st.toggle(
            "🌐", help="Ép buộc dùng web search"
        )
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Main Chat Flow
# ─────────────────────────────────────────────────────────────────────────────

def handle_rag_mode(prompt: str):
    """Xử lý câu hỏi ở chế độ RAG."""
    # Hiện câu hỏi người dùng
    with st.chat_message("user"):
        with st.expander("📝 Đánh giá câu hỏi"):
            st.write(f"Prompt gốc: {prompt}")

    # Lấy context
    with st.spinner("🤔 Đang tìm thông tin liên quan..."):
        context, docs = _get_rag_context(prompt)

    if not context:
        st.info("ℹ️ Không tìm thấy thông tin liên quan trong tài liệu hoặc web.")

    # Sinh câu trả lời
    with st.spinner("🤖 Đang suy nghĩ..."):
        try:
            agent = get_rag_agent()
            full_prompt = _build_prompt(prompt, context)
            response = agent.run(full_prompt)
            answer = response.content

            st.session_state.history.append({"role": "assistant", "content": answer})

            with st.chat_message("assistant"):
                st.markdown(answer)

                # Hiển thị nguồn tài liệu nếu có
                if not st.session_state.force_web_search and docs:
                    with st.expander("🔍 Xem nguồn tài liệu"):
                        for i, doc in enumerate(docs, 1):
                            stype = doc.metadata.get("source_type", "unknown")
                            icon = "📄" if stype == "pdf" else "🌐"
                            key = "file_name" if stype == "pdf" else "url"
                            name = doc.metadata.get(key, "unknown")
                            st.write(f"{icon} Nguồn {i}: {name}")
                            st.write(f"{doc.page_content[:200]}...")

        except Exception as e:
            st.error(f"❌ Lỗi sinh câu trả lời: {str(e)}")


def handle_simple_mode(prompt: str):
    """Xử lý câu hỏi ở chế độ không RAG (chat thuần)."""
    context = ""

    # Web search nếu được bật
    if st.session_state.force_web_search and st.session_state.use_web_search and st.session_state.exa_api_key:
        with st.spinner("🔍 Đang tìm kiếm web..."):
            try:
                agent = get_web_search_agent(
                    api_key=st.session_state.exa_api_key,
                    search_domains=st.session_state.search_domains,
                )
                results = agent.run(prompt).content
                if results:
                    context = f"Web Search Results:\n{results}"
                    st.info("ℹ️ Đang dùng web search.")
            except Exception as e:
                st.error(f"❌ Web search error: {str(e)}")

    with st.spinner("🤖 Đang suy nghĩ..."):
        try:
            agent = get_rag_agent()
            full_prompt = _build_prompt(prompt, context)
            response = agent.run(full_prompt)

            thinking, final_response = _extract_thinking(response.content)

            st.session_state.history.append({"role": "assistant", "content": final_response})

            with st.chat_message("assistant"):
                if thinking:
                    with st.expander("🤔 Xem quá trình suy luận"):
                        st.markdown(thinking)
                st.markdown(final_response)

        except Exception as e:
            st.error(f"❌ Lỗi sinh câu trả lời: {str(e)}")