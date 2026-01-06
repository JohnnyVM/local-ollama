#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODELS_FILE="${MODELS_FILE:-${SCRIPT_DIR}/models.txt}"
CONTAINER_NAME="${CONTAINER_NAME:-ollama}"
MODEL_ARG="${1:-}"
PROMPT_ARG="${2:-}"

if ! command -v podman >/dev/null 2>&1; then
  printf 'podman command not found; please install Podman.\n' >&2
  exit 1
fi

if [ ! -f "${MODELS_FILE}" ]; then
  printf 'Models file %s not found.\n' "${MODELS_FILE}" >&2
  exit 1
fi

select_model() {
  if [ -n "${MODEL_ARG}" ]; then
    printf '%s' "${MODEL_ARG}"
    return 0
  fi
  awk 'NF && $1 !~ /^#/ { print $1; exit }' "${MODELS_FILE}"
}

MODEL=$(select_model || true)
if [ -z "${MODEL}" ]; then
  printf 'Unable to determine a model (check %s).\n' "${MODELS_FILE}" >&2
  exit 1
fi

if ! podman container exists "${CONTAINER_NAME}" >/dev/null 2>&1; then
  printf 'Podman container %s not found. Start the stack first.\n' "${CONTAINER_NAME}" >&2
  exit 1
fi

if [ -n "${PROMPT_ARG}" ]; then
  if [ -f "${PROMPT_ARG}" ]; then
    PROMPT=$(cat "${PROMPT_ARG}")
  else
    PROMPT="${PROMPT_ARG}"
  fi
else
  PROMPT=$(cat <<'EOF'
You are a coding assistant. Review the following Python function and describe what it does, then suggest one improvement.

```python
def fizzbuzz(n):
    for i in range(1, n + 1):
        if i % 15 == 0:
            print("FizzBuzz")
        elif i % 3 == 0:
            print("Fizz")
        elif i % 5 == 0:
            print("Buzz")
        else:
            print(i)
```
EOF
)
fi

printf '>>> Sending prompt to %s in container %s\n\n' "${MODEL}" "${CONTAINER_NAME}"
printf '%s\n\n' "${PROMPT}"

podman exec -i "${CONTAINER_NAME}" ollama run "${MODEL}" <<EOF
${PROMPT}
EOF
