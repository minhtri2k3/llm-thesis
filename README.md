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

---

# 🇻🇳 Hướng Dẫn Cài Đặt (Tiếng Việt)

Repository này chứa hệ thống RAG (Retrieval-Augmented Generation) chạy hoàn toàn trên máy cá nhân, được xây dựng với **Qwen 3** (thông qua Ollama), **Docker** (cho Qdrant Vector Storage), và **Streamlit**.

## 📁 Cấu Trúc Thư Mục

*   `qwen_local_rag/`: Chứa ứng dụng Streamlit chính, cấu hình Langchain và các thư viện Python cần thiết.
*   `qdrant_storage/`: Thư mục lưu trữ dữ liệu vĩnh viễn được liên kết với Docker Qdrant container. Điều này đảm bảo rằng các vector dữ liệu tài liệu của bạn không bị mất đi mỗi khi khởi động lại cơ sở dữ liệu!

---

## 🚀 Cách Chạy Ứng Dụng Trên Windows

Làm theo các bước sau để thiết lập từ đầu:

### 1️⃣ Yêu Cầu Cấu Hình
Đảm bảo rằng bạn đã tải và cài đặt các công cụ sau trên máy tính Windows của mình:
1.  **Python 3.8+**
2.  **[Ollama](https://ollama.com/download)** (Bắt buộc để chạy các mô hình Ngôn ngữ Lớn).
3.  **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Phải luôn được mở và chạy ngầm).

### 2️⃣ Tải Mô Hình LLM cục bộ qua Ollama
Mở terminal (PowerShell hoặc Command Prompt) và tải các mô hình cần thiết:
```powershell
ollama pull qwen3:1.7b
ollama pull snowflake-arctic-embed
```
*(Bạn có thể kiểm tra xem Ollama đã chạy chưa bằng cách truy cập `http://localhost:11434` trên trình duyệt).*

### 3️⃣ Khởi Chạy Cơ Sở Dữ Liệu Vector (Qdrant)
Bạn bắt buộc phải chạy Qdrant bằng Docker. Mở terminal tại thư mục gốc của dự án này (`llm-thesis`) và chạy lệnh sau:
```powershell
docker run -d -p 6333:6333 -p 6334:6334 -v "${PWD}\qdrant_storage:/qdrant/storage" qdrant/qdrant
```
*(Bạn có thể kiểm tra xem Qdrant đã chạy chưa bằng cách truy cập bảng điều khiển tại `http://localhost:6333/dashboard`).*

### 4️⃣ Cài Đặt Thư Viện Python
Mở terminal và di chuyển vào thư mục `qwen_local_rag`, sau đó cài đặt các gói thư viện:
```powershell
cd qwen_local_rag
pip install -r requirements.txt
```

### 5️⃣ Khởi Chạy Ứng Dụng
Trong lúc cả Ollama và Docker container đang hoạt động ngầm, hãy chạy giao diện Streamlit:
```powershell
streamlit run qwen_local_rag_agent.py
```
*(Lệnh này sẽ tự động mở tab trình duyệt tại địa chỉ `http://localhost:8501`, nơi bạn có thể tải file PDF và trò chuyện trực tiếp với Qwen).*

---

### 💡 Khắc Phục Sự Cố (Troubleshooting)
*   **"Error checking Docker Engine"**: Đảm bảo Docker Desktop đã mở hoàn toàn và biểu tượng cá voi hiển thị ở khay hệ thống (góc dưới bên phải màn hình).
*   **"Ollama is not recognized"**: Hãy chắc chắn bạn đã khởi động lại terminal hoàn toàn sau khi cài đặt Ollama để máy tính cập nhật các biến môi trường.
*   **Lỗi Streamlit Module**: Đảm bảo bạn đang sử dụng đúng môi trường Python (nếu có) và đã chạy lệnh `pip install -r requirements.txt` thành công.
