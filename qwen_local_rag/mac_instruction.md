# Mac Instructions for Qwen Local RAG

## 1. Prerequisites
- **Homebrew** (Optional but recommended):
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- **Ollama**: Download and install the Mac version from [ollama.com](https://ollama.com/download/mac).
- **Python 3.8+**: Ensure you have Python installed (`brew install python`).
- **Google Cloud SQL Auth Proxy**: Since the current code connects to Google Cloud SQL (PostgreSQL), you need to run the Cloud SQL proxy.
  ```bash
  curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.darwin.arm64
  chmod +x cloud-sql-proxy
  ```
  *(Note: Use `darwin.amd64` instead of `darwin.arm64` if you are on an Intel Mac).*

## 2. Prepare the Environment
Open your terminal and run:

```bash
# Navigate to the project folder
cd path/to/your/qwen_local_rag

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Pull Models in Ollama
Make sure the Ollama app is open and running in your Mac menu bar.

```bash
# Pull the language model
ollama pull qwen3:1.7b 

# Pull the embedding model
ollama pull snowflake-arctic-embed
```

## 4. Connect to Google Database
The application relies on a Google Cloud SQL instance instead of a typical local database. Ensure you are authenticated with GCP, then start the proxy.
```bash
# Login to Google Cloud
gcloud auth application-default login

# Start the proxy (replace with the correct instance connection name if needed)
./cloud-sql-proxy dev-playground-0126:us-central1:dev-playground-db-instance
```
*(Leave this terminal tab open).*

## 5. Run the Application
Open a new terminal tab, navigate to your project directory, activate your environment, and start Streamlit:

```bash
source venv/bin/activate
streamlit run app.py
```
