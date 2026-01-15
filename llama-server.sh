podman run --rm -it \
  --device nvidia.com/gpu=all \
  --hooks-dir=/usr/share/containers/oci/hooks.d \
  -p 8080:8080 \
  -v /media/shared/llama-models:/models:ro,Z \
  -v ./promts:/promts:ro,Z \
  llama-server:latest \
  -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  -c 16384 \
  -ngl 30 \
  -b 64 \
  --host 0.0.0.0 \
  --chat-template-file /promts/qwen_soft_tools.jinja \
  --port 8080 \
   2>&1 | tee llama_server.log
