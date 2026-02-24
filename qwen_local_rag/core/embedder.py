# =============================================================================
# core/embedder.py — Wrapper LangChain-compatible cho OllamaEmbedder (agno)
# Tách riêng để dễ swap embedding model (ví dụ đổi sang OpenAI, HuggingFace…)
# =============================================================================

from typing import List
from langchain_core.embeddings import Embeddings
from agno.knowledge.embedder.ollama import OllamaEmbedder
from config import EMBEDDING_MODEL


class OllamaEmbedderr(Embeddings):
    """
    Adapter bọc agno.OllamaEmbedder để tương thích với LangChain Embeddings interface.
    Nếu muốn đổi provider embedding, chỉ cần thay class này.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.embedder = OllamaEmbedder(id=model_name, dimensions=1024)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self.embedder.get_embedding(text)