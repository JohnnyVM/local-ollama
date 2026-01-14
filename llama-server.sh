podman run --rm -it \
  --device nvidia.com/gpu=all \
  --hooks-dir=/usr/share/containers/oci/hooks.d \
  -p 8080:8080 \
  -v /media/shared/llama-models:/models:ro,Z \
  llama-server:latest \
  -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  -c 16384 \
  -ngl 30 \
  -b 64 \
  --host 0.0.0.0 \
  --port 8080
