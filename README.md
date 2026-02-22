# 🐋 Qwen 3 Local RAG Reasoning Agent

This repository contains a full locally-run Retrieval-Augmented Generation (RAG) system built with **Qwen 3** (via Ollama), **Docker** (for Qdrant Vector Storage), and **Streamlit**.

## 📁 Repository Structure

*   `qwen_local_rag/`: Contains the primary Streamlit application, Langchain configurations, and Python dependencies.
*   `qdrant_storage/`: A persistent storage folder that the Docker Qdrant container maps to. This ensures that your vector document embeddings are not lost between database restarts!

---

## 🚀 How to Run Locally on Windows

Follow these steps to set everything up from scratch:

### 1️⃣ Prerequisites
Make sure you have downloaded and installed the following tools on your Windows machine:
1.  **Python 3.8+**
2.  **[Ollama](https://ollama.com/download)** (Required to run the underlying Language Models).
3.  **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Must be opened and actively running in the background).

### 2️⃣ Download Local LLMs via Ollama
Open your terminal (PowerShell or Command Prompt) and pull the necessary models:
```powershell
ollama pull qwen3:1.7b
ollama pull snowflake-arctic-embed
```
*(You can verify Ollama is running by visiting `http://localhost:11434` in your browser).*

### 3️⃣ Start the Qdrant Vector Database
You must run Qdrant using Docker. Open your terminal at the root of this project folder (`llm-thesis`) and run:
```powershell
docker run -d -p 6333:6333 -p 6334:6334 -v "${PWD}\qdrant_storage:/qdrant/storage" qdrant/qdrant
```
*(You can verify Qdrant is running by visiting its dashboard at `http://localhost:6333/dashboard`).*

### 4️⃣ Install Python Dependencies
Open your terminal and navigate inside the `qwen_local_rag` folder, then install the packages:
```powershell
cd qwen_local_rag
pip install -r requirements.txt
```

### 5️⃣ Launch the Application
With both Ollama and the Docker container running in the background, start the Streamlit UI:
```powershell
streamlit run qwen_local_rag_agent.py
```
*(This will automatically open your browser to `http://localhost:8501` where you can upload PDFs and chat with Qwen).*

---

### 💡 Troubleshooting
*   **"Error checking Docker Engine"**: Make sure Docker Desktop is fully launched and your system tray shows the whale icon.
*   **"Ollama is not recognized"**: Ensure you have restarted your terminal completely after installing Ollama so your system variables refresh.
*   **Streamlit Module Errors**: Ensure you have activated your Python environment (if you are using one) and successfully ran `pip install -r requirements.txt`.
