# Ollama + Podman bootstrap

This repository contains a small setup that runs [Ollama](https://ollama.com/) locally with Podman/Podman Compose and preloads a curated list of lightweight coding models (<~4 GB VRAM targets). It also ships with a smoke-test helper for confirming end-to-end responses.

## Prerequisites

- Podman 4.6+ with the `podman compose` plugin (or Docker Compose compatibility mode).
- Sufficient disk space for downloaded GGUF model files (several gigabytes).
- (Optional) NVIDIA GPU; VRAM limits are considered in the default model list.

## Quick start

```bash
# Launch the stack (from the repository root)
podman compose -f podman/compose.yaml up -d

# Watch logs while models preload
podman logs -f ollama

# Run the built-in verification prompt
./podman/verify.sh
```

### Customise the preload list

Edit `podman/models.txt` to contain one model reference per line. Blank lines and lines starting with `#` are ignored. The entrypoint script pulls any missing models on first boot and skips models already cached inside `podman/data`.

After editing the model list:

```bash
podman compose -f podman/compose.yaml restart ollama
podman logs -f ollama
```

### Configuration knobs

Environment variables recognised by `podman/entrypoint.sh`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODEL_LIST_FILE` | `/models/preload.txt` | Alternate path to the newline-delimited model list. |
| `OLLAMA_HOME` | `/root/.ollama` | Override Ollama data/cache directory inside the container. |
| `OLLAMA_WAIT_RETRIES` | `40` | Number of 1-second retries while waiting for the API to come online before pulling models. |

Adjust or extend these values inside `podman/compose.yaml` if needed.

## Verification helper

`podman/verify.sh` is a convenience wrapper that:

1. Selects the first non-comment entry in `podman/models.txt` (or uses arguments provided).
2. Submits a sample prompt via `podman exec` to the running `ollama` container.
3. Prints the model response to standard output.

Usage examples:

```bash
# default model, bundled FizzBuzz prompt
./podman/verify.sh

# choose explicit model
./podman/verify.sh qwen2.5-coder:1.5b

# prompt text inline
./podman/verify.sh qwen2.5-coder:1.5b "Explain the SOLID principles."

# prompt from file
./podman/verify.sh qwen2.5-coder:1.5b ./prompts/refactor.txt
```

## Podman data volume

Downloaded models and Ollama metadata are mounted under `podman/data`. A `.gitignore` is included to keep the runtime cache out of version control.

## Next steps

- See `EXAMPLES.md` for wiring this local instance into the open-source *opencode* agent.
- Adjust health checks or ports in `podman/compose.yaml` if running alongside other services.
- Consider scripting `podman compose down` or pruning cached models when storage is tight.
