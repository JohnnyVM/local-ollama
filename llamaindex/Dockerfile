FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/hf \
    HF_HUB_CACHE=/hf/hub \
    HF_HUB_DOWNLOAD_TIMEOUT=120 \
    HF_HUB_ETAG_TIMEOUT=1800

WORKDIR /app

RUN pip install --no-cache-dir \
    "mcp[cli]" \
    llama-index \
    llama-index-vector-stores-faiss \
    faiss-cpu \
    llama-index-embeddings-fastembed \
    fastembed \
    beautifulsoup4 \
    lxml

# Pre-cache embedding model into /hf (NOT /data) so it isn't hidden by /data volume
RUN python - <<'PY'
from fastembed import TextEmbedding
TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir="/hf/hub")
print("fastembed model cached in /hf")
PY

COPY kb_mcp_server.py /app/kb_mcp_server.py

# Persist KB and HF cache as separate volumes
VOLUME ["/data", "/hf"]

ENTRYPOINT ["python", "/app/kb_mcp_server.py", "--data-dir", "/data"]
