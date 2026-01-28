FROM python:3.11-slim

# Basic runtime deps (faiss-cpu ships wheels; this keeps it simple)
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies:
# - mcp: MCP python sdk
# - llama-index: core
# - llama-index-vector-stores-faiss + faiss-cpu: local vector store
# - llama-index-embeddings-fastembed + fastembed: local embeddings
RUN pip install --no-cache-dir \
    "mcp[cli]" \
    llama-index \
    llama-index-vector-stores-faiss \
    faiss-cpu \
    llama-index-embeddings-fastembed \
    fastembed

COPY kb_mcp_server.py /app/kb_mcp_server.py

# Persist KB on a volume
VOLUME ["/data"]

# MCP uses stdio, so no ports required
ENTRYPOINT ["python", "/app/kb_mcp_server.py", "--data-dir", "/data"]
