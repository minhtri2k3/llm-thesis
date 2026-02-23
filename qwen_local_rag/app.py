import streamlit as st

from config import APP_TITLE, APP_INFO
from ui.sidebar import init_session_state, render_sidebar
from ui.chat import (
    render_document_upload,
    render_chat_history,
    render_chat_input,
    handle_rag_mode,
    handle_simple_mode,
)


def main():
    init_session_state()

    st.title(APP_TITLE)
    for info in APP_INFO:
        st.info(info)

    render_sidebar()

    if st.session_state.rag_enabled:
        render_document_upload()

    render_chat_history()

    prompt = render_chat_input()

    if prompt:
        st.session_state.history.append({"role": "user", "content": prompt})

        if st.session_state.rag_enabled:
            handle_rag_mode(prompt)
        else:
            handle_simple_mode(prompt)
    else:
        st.warning(
            "Bạn có thể chat trực tiếp với Qwen/Gemma! "
            "Bật RAG mode để upload tài liệu."
        )


if __name__ == "__main__":
    main()