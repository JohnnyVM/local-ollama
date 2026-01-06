# Integration examples

This document collects short walkthroughs that exercise the local Ollama stack and wire it into the open-source **opencode** agent environment.

## 1. Smoke-test with the bundled script

1. Ensure the Podman stack is running (`podman compose -f podman/compose.yaml up -d`).
2. Tail the logs until you see `Model preload cycle complete.`
3. Execute the helper:
   ```bash
   ./podman/verify.sh
   ```
4. Confirm a natural-language response describing the sample FizzBuzz function.

Arguments let you target a specific model or prompt:
```bash
./podman/verify.sh codegemma:2b "Review this TypeScript snippet and suggest a refactor."
```

## 2. Query the API directly

The Ollama HTTP API is exposed on `http://127.0.0.1:11434`. To check the status:

```bash
curl http://127.0.0.1:11434/api/version
```

Send a one-off generation request:

```bash
curl http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
        "model": "qwen2.5-coder:1.5b",
        "prompt": "Summarize bubble sort in two sentences."
      }'
```

## 3. Configure opencode to use the local Ollama instance

> **Note:** opencode builds may package different configuration surfaces. The examples below show common patterns; adjust to match your installation.

### 3.1 Using the global configuration file (JSONC)

Newer opencode builds ship a JSONC schema (see `https://opencode.ai/config.json`). Create or edit `~/.config/opencode/opencode.jsonc` with content like:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "ollama/qwen2.5-coder:1.5b",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama",
      "options": {
        "baseURL": "http://127.0.0.1:11434/v1"
      },
      "models": {
        "qwen2.5-coder:1.5b": {
          "name": "qwen2.5-coder:1.5b",
          "reasoning": true,
          "tools": true
        },
        "codegemma:2b": {
          "name": "codegemma:2b",
          "reasoning": true,
          "tools": true
        },
        "stable-code:3b": {
          "name": "stable-code:3b",
          "reasoning": true,
          "tools": true
        }
      }
    }
  }
}
```

Adjust the `model` field and the `models` map to match whatever entries you have in `podman/models.txt`. Once saved, start opencode (no extra flags required if you keep the global default):

```bash
opencode
```

If your opencode build still expects the legacy config shape, run `opencode config --help` (or consult upstream docs) and adapt the values accordingly.

### 3.2 Using environment variables

Some opencode distributions honour environment overrides. Set them before launching:

```bash
export OPENCODE_PROVIDER=ollama
export OPENCODE_OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
export OPENCODE_MODEL=qwen2.5-coder:1.5b
opencode
```

If the binary exposes CLI flags, the equivalent might look like:

```bash
opencode --provider ollama \
         --base-url http://127.0.0.1:11434/v1 \
         --model qwen2.5-coder:1.5b
```

### 3.3 Verify connectivity inside opencode

Once opencode is pointing at the local instance:

1. Run `:models` (or the provider-specific listing command) to check the model inventory.
2. Issue a short prompt—e.g. "Generate a Python function that reverses a list".
3. Watch `podman logs -f ollama` in another terminal to confirm requests are flowing through.

If opencode reports connection issues:

- Re-run `curl http://127.0.0.1:11434/api/version` to ensure the service is healthy.
- Verify the selected model exists (`podman exec ollama ollama list`).
- Check for firewalls or port conflicts that block `127.0.0.1:11434`.
