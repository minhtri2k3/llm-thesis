# =============================================================================
# loaders/web_loader.py — Load và chunk nội dung từ URL
# Tách riêng để dễ tuỳ chỉnh CSS selector hoặc thêm loader khác
# =============================================================================

from datetime import datetime
from typing import List

import bs4
import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP

# CSS class cần scrape — chỉnh tại đây nếu target site có cấu trúc khác
SCRAPE_CLASSES = ("post-content", "post-title", "post-header", "content", "main")


def process_web(url: str) -> List:
    """
    Scrape nội dung từ URL, chunk thành các đoạn nhỏ.

    Args:
        url: URL cần scrape.

    Returns:
        Danh sách LangChain Document sau khi chunk. Trả về [] nếu lỗi.
    """
    try:
        print(f"[DEBUG][WEB] Starting scrape for URL: {url}")
        loader = WebBaseLoader(
            web_paths=(url,),
            bs_kwargs=dict(
                parse_only=bs4.SoupStrainer(class_=SCRAPE_CLASSES)
            ),
        )
        documents = loader.load()
        print(f"[DEBUG][WEB] Loaded {len(documents)} raw documents from {url}")

        # Gắn metadata nguồn
        for doc in documents:
            doc.metadata.update(
                {
                    "source_type": "url",
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(documents)
        print(f"[DEBUG][WEB] Split into {len(chunks)} chunks for URL: {url}")
        return chunks

    except Exception as e:
        st.error(f"🌐 Web processing error: {str(e)}")
        return []