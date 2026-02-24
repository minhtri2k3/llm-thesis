# =============================================================================
# core/vector_store.py — Quản lý Qdrant: khởi tạo client, tạo collection, add docs
# Tách riêng để dễ swap vector DB (Chroma, Pinecone, Weaviate…)
# =============================================================================

from typing import List, Optional
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

from config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE
from core.embedder import OllamaEmbedderr


def init_qdrant() -> Optional[QdrantClient]:
    """
    Kết nối tới Qdrant local (Docker).
    Trả về None nếu kết nối thất bại.
    """
    try:
        return QdrantClient(url=QDRANT_URL)
    except Exception as e:
        st.error(f"🔴 Qdrant connection failed: {str(e)}")
        return None


def create_vector_store(
    client: QdrantClient,
    texts: List,
    collection_name: str = COLLECTION_NAME,
) -> Optional[QdrantVectorStore]:
    """
    Tạo collection (nếu chưa có) và nạp documents vào Qdrant.

    Args:
        client: QdrantClient đã khởi tạo.
        texts: Danh sách LangChain Document đã được chunk.
        collection_name: Tên collection trong Qdrant.

    Returns:
        QdrantVectorStore nếu thành công, None nếu lỗi.
    """
    try:
        # Tạo collection mới nếu chưa tồn tại
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            st.success(f"📚 Đã tạo collection mới: {collection_name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise e  # Lỗi thật sự, không phải "đã tồn tại"

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=OllamaEmbedderr(),
        )

        with st.spinner("📤 Đang upload documents lên Qdrant..."):
            vector_store.add_documents(texts)
            st.success("✅ Documents đã được lưu thành công!")

        return vector_store

    except Exception as e:
        st.error(f"🔴 Vector store error: {str(e)}")
        return None


def retrieve_documents(
    vector_store: QdrantVectorStore,
    query: str,
    threshold: float,
    top_k: int = 5,
) -> List:
    """
    Tìm kiếm documents liên quan theo similarity score threshold.

    Args:
        vector_store: QdrantVectorStore đã khởi tạo.
        query: Câu hỏi của người dùng.
        threshold: Ngưỡng similarity (0.0 – 1.0).
        top_k: Số lượng kết quả tối đa.

    Returns:
        Danh sách Document phù hợp.
    """
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": top_k, "score_threshold": threshold},
    )
    return retriever.invoke(query)