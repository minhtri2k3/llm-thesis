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
  brew install --cask google-cloud-sdk
  ```

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

If you already created `venv` before new dependencies were added:

```bash
source venv/bin/activate
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
gcloud auth application-default set-quota-project dev-playground-0126

# Start the proxy (replace with the correct instance connection name if needed)
~/cloud-sql-proxy \
  --port=5432 \
  dev-playground-0126:us-central1:dev-playground-db-instance

```

Optional: 
```
mv ~/cloud-sql-proxy /usr/local/bin/cloud-sql-proxy 
```
Then you can 
```
cloud-sql-proxy --port=5432 dev-playground-0126:us-central1:dev-playground-db-instance
```
*(Leave this terminal tab open).*

## 5. Configure DB env for pre-processing script
The `pre_processing/processing_data.py` script now requires environment variables (no hardcoded DB credentials):

```bash
export PGDATABASE="agentic-rag"
export PGUSER="dev-playground"
export PGPASSWORD="<your-db-password>"
export PGHOST="127.0.0.1"   # optional
export PGPORT="5432"        # optional
```

Run diagnostics:

```bash
source qwen_local_rag/.env && python3 qwen_local_rag/pre_processing/processing_data.py doctor
```

If diagnostics pass, initialize DB tables:

```bash
python3 qwen_local_rag/pre_processing/processing_data.py init-db
```

Ingest Kaggle clothing data directly into Cloud SQL:

```bash
python3 qwen_local_rag/pre_processing/processing_data.py ingest-kaggle
```

## 6. Run the Application
Open a new terminal tab, navigate to your project directory, activate your environment, and start Streamlit:

```bash
source venv/bin/activate
streamlit run app.py
```

## 7. Cloud SQL auth troubleshooting
If proxy shows:

`invalid_grant` or `invalid_rapt`

this means ADC re-authentication is required.

Recovery steps:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project dev-playground-0126
~/cloud-sql-proxy --port=5432 dev-playground-0126:us-central1:dev-playground-db-instance
source qwen_local_rag/.env && python3 qwen_local_rag/pre_processing/processing_data.py doctor
```

Error mapping:
- `invalid_rapt`: Re-auth required for current ADC account.
- `connection refused`: Proxy is not listening on `127.0.0.1:5432`.
- `server closed the connection unexpectedly`: Proxy accepted local connection but could not connect upstream (often ADC/IAM).

## 8. Troubleshooting SSL Certificate Errors
If you see an error like:

`SSL: CERTIFICATE_VERIFY_FAILED`

run these commands in the same terminal where you start the app:

```bash
pip install certifi
export SSL_CERT_FILE=$(python -m certifi)
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
streamlit run app.py
```
