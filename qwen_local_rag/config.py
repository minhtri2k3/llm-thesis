# =============================================================================
# config.py — Toàn bộ hằng số và cấu hình mặc định của ứng dụng
# Chỉ cần sửa file này khi muốn thay đổi model, endpoint, chunk size, v.v.
# =============================================================================

# --- Qdrant ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "test-qwen-r1"
VECTOR_SIZE = 1024
VECTOR_DISTANCE = "Cosine"

# --- Embedding ---
EMBEDDING_MODEL = "snowflake-arctic-embed"

# --- Web Search Agent ---
WEB_SEARCH_MODEL = "llama3.2"
WEB_SEARCH_NUM_RESULTS = 5
DEFAULT_SEARCH_DOMAINS = ["arxiv.org", "wikipedia.org", "github.com", "medium.com"]

# --- Document Processing ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_SIMILARITY_THRESHOLD = 0.7
RETRIEVER_TOP_K = 5

# --- LLM Models ---
AVAILABLE_MODELS = [
    "qwen3:1.7b",
    "gemma3:1b",
    "gemma3:4b",
    "deepseek-r1:1.5b",
    "qwen3:8b",
]
DEFAULT_MODEL = "qwen3:1.7b"

MODEL_HELP = """
- qwen3:1.7b: Nhẹ, phù hợp máy cấu hình thấp (MoE)
- gemma3:1b: Mạnh hơn, cần GPU/RAM tốt hơn (32k context)
- gemma3:4b: Multimodal (Vision), 128k context
- deepseek-r1:1.5b: Reasoning model nhỏ
- qwen3:8b: Mạnh nhất, cần GPU/RAM cao

Chọn model phù hợp với phần cứng của bạn.
"""

# --- App Info ---
APP_TITLE = "🐋 Qwen 3 Local RAG Reasoning Agent"
APP_INFO = [
    "**Qwen3:** Dòng LLM thế hệ mới nhất của Qwen series, hỗ trợ cả dense và MoE models.",
    "**Gemma 3:** Multimodal (text + image), context 128K, hỗ trợ 140+ ngôn ngữ.",
]