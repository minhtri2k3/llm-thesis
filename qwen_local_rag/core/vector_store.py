# =============================================================================
# core/vector_store.py — Quản lý Qdrant: khởi tạo client, tạo collection, add docs
# Tách riêng để dễ swap vector DB (Chroma, Pinecone, Weaviate…)
# =============================================================================

from typing import List, Optional
import streamlit as st
import asyncio
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore

from config import COLLECTION_NAME, VECTOR_SIZE
from core.embedder import OllamaEmbedderr


def init_cloud_sql() -> Optional[PostgresEngine]:
    """
    Kết nối tới Google Cloud SQL PostgreSQL database thông qua cloud-sql-proxy.
    Trả về None nếu kết nối thất bại.
    """
    try:
        import sys
        # asyncpg requires the SelectorEventLoop on Windows, otherwise it throws WinError 10054
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # We need an event loop for the async engine initialization
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Initialize Google Cloud SQL Python Connector natively
        print("[DEBUG][DB] Initializing Cloud SQL engine...")
        engine = loop.run_until_complete(PostgresEngine.afrom_instance(
            project_id="dev-playground-0126",
            region="us-central1",
            instance="dev-playground-db-instance",
            database="agentic-rag",
            user="dev-playground",
            password='4hrEEZZ5=M"1FXkE',
        ))
        # Initialize the vector table (catching error if it already exists)
        from sqlalchemy.exc import ProgrammingError
        try:
            loop.run_until_complete(engine.ainit_vectorstore_table(
                table_name=COLLECTION_NAME.replace("-", "_"),
                vector_size=VECTOR_SIZE
            ))
        except ProgrammingError as e:
            if "already exists" not in str(e):
                raise
        print("[DEBUG][DB] Cloud SQL engine and vector table ready.")
        return engine
    except Exception as e:
        print(f"[DEBUG][DB] Cloud SQL connection failed: {e}")
        st.error(f"🔴 Cloud SQL connection failed: {str(e)}")
        return None


def create_vector_store(
    engine: PostgresEngine,
    texts: List,
    collection_name: str = COLLECTION_NAME,
) -> Optional[PostgresVectorStore]:
    """
    Khởi tạo vector store và nạp documents vào Google Cloud SQL.

    Args:
        engine: PostgresEngine đã khởi tạo.
        texts: Danh sách LangChain Document đã được chunk.
        collection_name: Tên collection trong Cloud SQL.

    Returns:
        PostgresVectorStore nếu thành công, None nếu lỗi.
    """
    try:
        print(f"[DEBUG][VEC] Creating vector store '{collection_name}' with {len(texts)} docs")
        vector_store = PostgresVectorStore.create_sync(
            engine=engine,
            table_name=collection_name.replace("-", "_"),
            embedding_service=OllamaEmbedderr(),
        )

        with st.spinner("📤 Đang upload documents lên Cloud SQL..."):
            vector_store.add_documents(texts)
            print(f"[DEBUG][VEC] Successfully added {len(texts)} docs to vector store '{collection_name}'")
            st.success("✅ Documents đã được lưu thành công!")

        return vector_store

    except Exception as e:
        st.error(f"🔴 Vector store error: {str(e)}")
        return None


def retrieve_documents(
    vector_store: PostgresVectorStore,
    query: str,
    threshold: float,
    top_k: int = 5,
) -> List:
    """
    Tìm kiếm documents liên quan theo similarity score threshold.

    Args:
        vector_store: PostgresVectorStore đã khởi tạo.
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