# OpenHands Local Development

This folder contains Docker Compose and supporting files to run OpenHands locally with Docker (Colima or Docker Desktop) on macOS.

## Purpose

Run the OpenHands web UI (`agentic-pr-openhands-web`) with:
- Local Ollama LLM (via `host.docker.internal`)
- Sandbox/agent containers spawned per conversation (`oh-agent-server-*`)
- Persistent configuration in `~/.openhands-agentic-pr/`
- Runtime artifacts ignored by git (`.openhands-runtime/`)

## Prerequisites

- **Colima** (or Docker Desktop) with sufficient VM memory configured
- **Ollama** running on host (port 11434) with desired model pulled:
  ```bash
  ollama pull qwen3-coder:30b
  ```

## Colima Memory (Critical)

If `docker stats --no-stream` shows container limits around `1.913GiB`, your Colima VM is likely running with only 2GB RAM. OpenHands may start but conversations can hang, fail, or never show progress because the Docker runtime is starved.

Restart Colima with more memory:
```bash
make -f Makefile.openhands colima-restart COLIMA_CPU=8 COLIMA_MEMORY=12 COLIMA_DISK=100
```

Then verify:
```bash
make -f Makefile.openhands colima-status
make -f Makefile.openhands restart-clean
make -f Makefile.openhands stats
```

Docker Compose `mem_limit: 6g` cannot exceed the memory available to the Colima VM.

## Required Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `ollama/qwen3-coder:30b` | LLM to use (must be pulled in Ollama) |
| `LLM_BASE_URL` | `http://host.docker.internal:11434` | Ollama OpenAI-compatible endpoint |
| `LLM_API_KEY` | `local-llm` | API key (any value works for local Ollama) |
| `OPENHANDS_REPO_PATH` | repo root | Absolute path to repository |
| `OPENHANDS_PERSISTENCE_DIR` | `~/.openhands-agentic-pr` | Config persistence |
| `OPENHANDS_WEB_MEMORY_LIMIT` | `6g` | Memory limit for web container |
| `OPENHANDS_WEB_MEMORY_SWAP_LIMIT` | `8g` | Memory swap limit for web container |

## Quick Start (Colima)

```bash
cd infra/openhands

# 1. Copy and edit .env
cp .env.example .env
# Edit .env with your paths and LLM settings

# 2. Start Colima with enough memory (12GB recommended)
make -f Makefile.openhands colima-restart COLIMA_CPU=8 COLIMA_MEMORY=12 COLIMA_DISK=100

# 3. Clean restart OpenHands
make -f Makefile.openhands restart-clean

# 4. Verify
make -f Makefile.openhands status
make -f Makefile.openhands stats
```

Open the web UI at: **http://localhost:3000**

## Common Commands

```bash
# Colima management
make -f Makefile.openhands colima-status    # Show Colima status + Docker resources
make -f Makefile.openhands colima-start     # Start Colima (uses COLIMA_* vars)
make -f Makefile.openhands colima-restart   # Restart Colima with COLIMA_* vars
make -f Makefile.openhands colima-stop      # Stop Colima

# OpenHands web UI
make -f Makefile.openhands up               # Start web UI (pulls latest image)
make -f Makefile.openhands down             # Stop web UI
make -f Makefile.openhands restart-clean    # Clean restart (down + clean-agents + up)
make -f Makefile.openhands restart-clean-settings  # Full reset: stop, reset settings/profile, clean agents, start
make -f Makefile.openhands status           # Show OpenHands container status
make -f Makefile.openhands ps               # Show all Docker containers
make -f Makefile.openhands logs             # Follow web container logs
make -f Makefile.openhands agent-logs       # Follow newest sandbox container logs of newest sandbox container
make -f Makefile.openhands diagnose         # Full diagnostics
make -f Makefile.openhands config           # Show resolved docker-compose config
make -f Makefile.openhands env              # Show LLM env vars in web container
make -f Makefile.openhands ollama-test      # Test Ollama connectivity from Docker
make -f Makefile.openhands stats            # Show container memory stats

# Profiles & cleanup
make -f Makefile.openhands profiles         # Show persisted profile model values
make -f Makefile.openhands profile-debug    # Show raw profile/setting values for debugging
make -f Makefile.openhands clean-profiles   # Remove stale Ollama profile
make -f Makefile.openhands reset-llm-profile # Remove stale profile + show UI setup
make -f Makefile.openhands reset-openhands-settings  # Backup and remove settings.json + profiles/Ollama.json
make -f Makefile.openhands reset-llm-state  # Stop, reset settings/profile, clean agents (no restart)
make -f Makefile.openhands clean-agents     # Remove all oh-agent-server-* containers
make -f Makefile.openhands clean-cli        # Remove old CLI containers by image
make -f Makefile.openhands clean            # Full cleanup (down + clean-agents + clean-cli + clean-profiles)
make -f Makefile.openhands prune-containers # Prune all stopped containers

# Helpers
make -f Makefile.openhands config           # Show resolved docker-compose config
make -f Makefile.openhands stats            # docker stats --no-stream
```

## Container Types

| Container | Purpose |
|-----------|---------|
| `agentic-pr-openhands-web` | Main web UI (port 3000) |
| `oh-agent-server-*` | Per-conversation sandbox/agent servers |
| `agentic-pr/openhands-cli:local` | Old headless CLI containers (remove with `make clean-cli`) |

## Runtime Artifacts (Ignored by Git)

The following are runtime artifacts and are ignored by `.gitignore`:

- `.openhands-runtime/` - Conversation state and bash events (repo root)
- `infra/openhands/.openhands-runtime/` - Legacy path
- `infra/openhands/conversations/` - Legacy path
- `infra/openhands/bash_events/` - Legacy path
- `conversations/` - Legacy root path
- `bash_events/` - Legacy root path

These contain session-specific data (events, git changes, command output) and should not be committed.

After the fix, new agent-server logs should show conversation paths under:
```
/workspace/.openhands-runtime/conversations
/workspace/.openhands-runtime/bash_events
```
not:
```
/workspace/conversations
```

If logs still show `/workspace/conversations`, the agent-server environment is not receiving `OH_AGENT_SERVER_ENV`.

## Troubleshooting: LiteLLM "LLM Provider NOT provided"

### The Error
```
litellm.BadRequestError: LLM Provider NOT provided. Pass in the LLM provider you are trying to call.
You passed model=qwen3-coder:30b
```

### Root Cause
OpenHands/LiteLLM requires the **provider prefix** in the model name. The model must be:
```
ollama/qwen3-coder:30b
```
not:
```
qwen3-coder:30b
```

This can happen if:
1. The `LLM_MODEL` env var was set without the `ollama/` prefix
2. A persisted OpenHands profile (in `~/.openhands-agentic-pr/profiles/`) contains the bad model value
3. The UI was configured with the wrong model name

### Fix

1. **Set the correct model with prefix:**
   ```bash
   export LLM_MODEL="ollama/qwen3-coder:30b"
   export LLM_BASE_URL="http://host.docker.internal:11434"
   export LLM_API_KEY="local-llm"
   ```

2. **Remove stale persisted profile:**
   ```bash
   make -f Makefile.openhands clean-profiles
   ```

3. **Clean restart:**
   ```bash
   make -f Makefile.openhands clean
   make -f Makefile.openhands up
   ```

   Or use the combined target:
   ```bash
   make -f Makefile.openhands reset-llm-profile
   make -f Makefile.openhands up
   ```

4. **Verify in UI Settings:**
   - Model: `ollama/qwen3-coder:30b`
   - Base URL: `http://host.docker.internal:11434`
   - API Key: `local-llm`

   Not:
   - Model: `qwen3-coder:30b`

### Verify Fix
```bash
# Check no profile has the bad model
make -f Makefile.openhands profiles

# Check container status
make -f Makefile.openhands status

# Follow agent logs - should NOT show "LLM Provider NOT provided"
make -f Makefile.openhands agent-logs

# Validate container env vars
docker exec agentic-pr-openhands-web env | grep -E 'LLM_MODEL|LLM_BASE_URL|LLM_API_KEY'
```

Expected:
```
LLM_MODEL=ollama/qwen3-coder:30b
LLM_BASE_URL=http://host.docker.internal:11434
LLM_API_KEY=local-llm
```

## Troubleshooting: OllamaException "does not support thinking"

### The Error
```
OllamaException - {"error":"\"qwen3-coder:30b\" does not support thinking"}
```

### Root Cause
OpenHands persists LLM profile settings including model-level reasoning/thinking options like:
```json
"reasoning_effort": "high"
"extended_thinking_budget": 200000
"enable_encrypted_reasoning": true
```
But `qwen3-coder:30b` does not support these options. The persisted `settings.json` and `profiles/Ollama.json` files contain these options and they get sent to Ollama on every conversation.

### Fix

1. **Debug persisted settings:**
   ```bash
   make -f Makefile.openhands profile-debug
   ```

2. **Reset stale settings/profile and restart cleanly:**
   ```bash
   make -f Makefile.openhands restart-clean-settings
   ```

   Or step by step:
   ```bash
   make -f Makefile.openhands reset-llm-state
   make -f Makefile.openhands up
   ```

3. **Reopen UI and recreate the LLM profile with correct settings:**
   - Name: `Ollama`
   - Custom Model: `ollama/qwen3-coder:30b`
   - Base URL: `http://host.docker.internal:11434`
   - API key: `local-llm`
   - **Do NOT enable** model-level reasoning/thinking options

### Notes

- `settings.json` and `profiles/Ollama.json` are **automatically recreated** by OpenHands on restart and when you save the profile in the UI.
- `settings.json` is **backed up** before deletion (timestamped `.bak` file).
- Do NOT delete the entire `~/.openhands-agentic-pr/` directory; just the specific files mentioned above.

## Colima Diagnostics

```bash
make -f Makefile.openhands diagnose
```

Runs:
- `colima status`
- Docker info (CPUs, memory, OS)
- Resolved docker-compose config
- Container stats
- Web container memory limits + OOM status
- Last 300 lines of web container logs

## Verify Setup

```bash
# Check Ollama is reachable from Docker
make -f Makefile.openhands ollama-test

# Check web container is running
make -f Makefile.openhands status

# Check git status is clean of runtime artifacts
git status --short
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  macOS Host                                             │
│  ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  Ollama      │    │  Colima VM                   │  │
│  │  :11434      │    │  ┌────────────────────────┐  │  │
│  └──────┬───────┘    │  │ agentic-pr-openhands-web│  │  │
│         │            │  │  :3000 (web UI)         │  │  │
│         │            │  │  mounts:                │  │  │
│         │            │  │   /var/run/docker.sock  │  │  │
│         │            │  │   repo → /workspace     │  │  │
│         │            │  │   config → /.openhands  │  │  │
│         │            │  └───────────┬─────────────┘  │  │
│         │            │              │ spawns         │  │
│         │            │  ┌───────────▼─────────────┐  │  │
│         └────────────▶ │  oh-agent-server-*      │  │  │
│   host.docker.internal │  (per conversation)     │  │  │
│         │              │  mounts repo as /workspace│  │  │
│         │              └─────────────────────────┘  │  │
│         │                                           │  │
└─────────┴───────────────────────────────────────────┘
```

## `run-openhands.sh` (Headless CLI Mode)

The `run-openhands.sh` script runs OpenHands in headless mode (not the web UI). It's useful for automated tasks.

```bash
cd infra/openhands
./run-openhands.sh --headless --override-with-envs --task "Add tests"
```

Docker run flags must come before the image name. The script handles this correctly.