# 🐋 Qwen 3 Local RAG Reasoning Agent

This repository contains a full locally-run Retrieval-Augmented Generation (RAG) system built with **Qwen 3** (via Ollama), **Google Cloud SQL (PostgreSQL)** (for Vector Storage), and **Streamlit**.

## 📁 Repository Structure

*   `qwen_local_rag/`: Contains the primary Streamlit application (`app.py`), Langchain configurations (`core/`, `ui/`), and Python dependencies.
*   `qdrant_storage/`: *(Legacy)* A persistent storage folder that was previously used for the local Qdrant database.

---

## 🚀 How to Run Locally

Follow these steps to set everything up from scratch:

### 1️⃣ Prerequisites
Make sure you have downloaded and installed the following tools on your machine:
1.  **Python 3.8+**
2.  **[Ollama](https://ollama.com/download)** (Required to run the underlying Language Models).
3.  **[Google Cloud CLI](https://cloud.google.com/sdk/docs/install)** (Required to authenticate with the remote PostgreSQL vector database).

### 2️⃣ Download Local LLMs via Ollama
Open your terminal (PowerShell or Command Prompt) and pull the necessary models:
```powershell
ollama pull qwen3:1.7b
ollama pull snowflake-arctic-embed
```
*(You can verify Ollama is running by visiting `http://localhost:11434` in your browser).*

### 3️⃣ Authenticate with Google Cloud
Since the vector embeddings are stored in Google Cloud SQL, you must authenticate your local environment using the Google Cloud CLI. Open your terminal and run:
```bash
gcloud auth application-default login
```
*(A browser window will open. Please log in with the correct Google account that has `Cloud SQL Client` permissions for your project).*

### 4️⃣ Install Python Dependencies
Open your terminal and navigate inside the `qwen_local_rag` folder, then install the packages:
```powershell
cd qwen_local_rag
pip install -r requirements.txt
```

### 5️⃣ Launch the Application
With Ollama running and your Google Cloud credentials authenticated, start the Streamlit UI:
```bash
streamlit run app.py
```
*(This will automatically open your browser to `http://localhost:8501` where you can upload PDFs and chat with Qwen).*

---

### 💡 Troubleshooting
*   **"Cloud SQL connection failed"**: Make sure you ran `gcloud auth application-default login` and selected the correct email address with IAM permissions.
*   **"Ollama is not recognized"**: Ensure you have restarted your terminal completely after installing Ollama so your system variables refresh.
*   **Streamlit Module Errors**: Ensure you have activated your Python environment (if you are using one) and successfully ran `pip install -r requirements.txt`.
