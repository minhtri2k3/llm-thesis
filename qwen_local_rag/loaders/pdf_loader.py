import tempfile
from datetime import datetime
from typing import List

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP


def process_pdf(file) -> List:
    """Process an uploaded PDF file and return split document chunks with metadata."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file.getvalue())
            loader = PyPDFLoader(tmp_file.name)
            documents = loader.load()

        for doc in documents:
            doc.metadata.update({
                "source_type": "pdf",
                "file_name": file.name,
                "timestamp": datetime.now().isoformat()
            })

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        return text_splitter.split_documents(documents)

    except Exception as e:
        st.error(f"📄 PDF processing error: {str(e)}")
        return []