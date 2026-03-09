## Why

Project `qwen_local_rag` chứa **2 hệ thống RAG hoàn toàn tách biệt** cùng tồn tại:
1. **Production** (Fashion Agent): FastAPI + Gemini + Qdrant + FashionSigLIP — đang chạy trong Docker.
2. **Legacy** (Streamlit RAG): Streamlit + Ollama/Agno + LangChain + Google Cloud SQL — **không còn sử dụng**.

Legacy code gây nhầm lẫn, tăng Docker image size (do `COPY . .`), và **2 file test chứa hardcoded credentials** (password Google Cloud SQL) là rủi ro bảo mật.

## What Changes

- **REMOVE** toàn bộ module `core/` (agents.py, embedder.py, vector_store.py, mcp_manager.py) — Streamlit-based agents dùng Agno + Ollama
- **REMOVE** toàn bộ module `loaders/` (pdf_loader.py, web_loader.py) — LangChain document loaders
- **REMOVE** toàn bộ module `ui/` (chat.py, sidebar.py, mcp_panel.py) — Streamlit UI
- **REMOVE** `mcp_config.py` — empty file (0 bytes)
- **REMOVE** `test_native_connector.py`, `test_pure_asyncpg.py` — ⚠️ chứa hardcoded Google Cloud SQL password
- **REMOVE** `requirements.txt` — legacy dependencies (agno, streamlit, langchain-google-cloud-sql-pg)
- **REMOVE** `mac_instruction.md` — trùng nội dung với `docs/development.md`
- **REMOVE** empty `images/` directory
- **REMOVE** `.amazonq/` directory — Amazon Q IDE config không dùng
- **UPDATE** `.dockerignore` — thêm patterns tránh lặp lại nếu folder tái xuất hiện
- **UPDATE** `.gitignore` — thêm `.amazonq/`

## Capabilities

### New Capabilities
- `legacy-cleanup`: Xóa toàn bộ code legacy không liên quan đến Fashion Agent pipeline, bao gồm hardcoded credentials cleanup

### Modified Capabilities
_(Không có capability nào bị thay đổi — chỉ xóa code không dùng)_

## Impact

- **Code removed**: ~14 Python files, 3 empty files, 1 empty directory, 1 redundant markdown
- **Production code**: Không bị ảnh hưởng — cross-reference xác nhận không production file nào import legacy modules
- **Docker image**: Nhỏ hơn do bớt file copy vào container
- **Security**: Xóa 2 file chứa hardcoded password (test_native_connector.py, test_pure_asyncpg.py)
- **Dependencies**: `requirements.txt` (legacy) bị xóa — production dùng `requirements-docker.txt`
