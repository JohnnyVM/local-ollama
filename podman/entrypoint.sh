#!/bin/sh
set -eu

log() {
  printf '%s\n' "$*" >&2
}

MODEL_LIST_FILE="${MODEL_LIST_FILE:-/models/preload.txt}"
OLLAMA_HOME="${OLLAMA_HOME:-/root/.ollama}"
WAIT_RETRIES="${OLLAMA_WAIT_RETRIES:-40}"

mkdir -p "${OLLAMA_HOME}"

if [ ! -f "${MODEL_LIST_FILE}" ]; then
  log "Model list file ${MODEL_LIST_FILE} not found; starting Ollama normally."
  exec /bin/ollama serve
fi

if [ ! -s "${MODEL_LIST_FILE}" ]; then
  log "Model list file ${MODEL_LIST_FILE} is empty; starting Ollama normally."
  exec /bin/ollama serve
fi

/bin/ollama serve &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null' EXIT INT TERM

log "Waiting for Ollama API to become ready..."
check_ready() {
  if ollama list >/dev/null 2>&1; then
    return 0
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -fsS http://localhost:11434/api/version >/dev/null 2>&1 && return 0
  fi
  return 1
}

TRIES=0
until check_ready; do
  TRIES=$((TRIES + 1))
  if [ "${TRIES}" -ge "${WAIT_RETRIES}" ]; then
    log "Timed out waiting for Ollama API."
    exit 1
  fi
  sleep 1
done

log "Ollama API is ready; ensuring models from ${MODEL_LIST_FILE} are available."
while IFS= read -r line || [ -n "${line}" ]; do
  MODEL=$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  if [ -z "${MODEL}" ]; then
    continue
  fi
  case "${MODEL}" in
    \#*)
      continue
      ;;
  esac
  if ollama list 2>/dev/null | awk -v target="${MODEL}" 'BEGIN { found=0 } NR>1 { if ($1 == target) { found=1; exit } } END { exit(found ? 0 : 1) }'; then
    log "Model ${MODEL} already present; skipping."
    continue
  fi
  log "Pulling model: ${MODEL}"
  ollama pull "${MODEL}"
done < "${MODEL_LIST_FILE}"

log "Model preload cycle complete."

kill "${SERVER_PID}" 2>/dev/null || true
trap - EXIT INT TERM

exec /bin/ollama serve
