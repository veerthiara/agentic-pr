#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${OPENHANDS_DOCKER_IMAGE:-agentic-pr/openhands-cli:local}"
PERSISTENCE_DIR="${OPENHANDS_PERSISTENCE_DIR:-$HOME/.openhands-agentic-pr}"
LLM_MODEL_VALUE="${LLM_MODEL:-ollama/qwen3-coder:30b}"
LLM_BASE_URL_VALUE="${LLM_BASE_URL:-http://host.docker.internal:11434/v1}"
LLM_API_KEY_VALUE="${LLM_API_KEY:-local-llm}"
REPO_PATH="${OPENHANDS_REPO_PATH:-$PWD}"
REPO_PATH="$(cd "$REPO_PATH" && pwd)"
CONTAINER_NAME="${OPENHANDS_CONTAINER_NAME:-agentic-pr-openhands-cli}"
CLI_MEMORY="${OPENHANDS_CLI_MEMORY_LIMIT:-6g}"
CLI_MEMORY_SWAP="${OPENHANDS_CLI_MEMORY_SWAP_LIMIT:-8g}"

usage() {
  cat <<EOF
run-openhands.sh: Docker wrapper for OpenHands headless mode

This script runs the official OpenHands container without requiring a global
OpenHands installation on the host.

Required runtime environment:
  docker
  LLM_MODEL
  LLM_BASE_URL (defaults to host.docker.internal Ollama OpenAI endpoint)
  LLM_API_KEY (any placeholder works for local Ollama)

Example:
  run-openhands.sh --headless --override-with-envs --task "Add tests"
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--version" || "${1:-}" == "-v" -v ]]; then
  docker info >/dev/null
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    docker build -t "${IMAGE}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}" >/dev/null
  fi
  docker run --rm -i "${IMAGE}" "openhands --version"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found" >&2
  exit 127
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  docker build -t "${IMAGE}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}" >/dev/null
fi

mkdir -p "${PERSISTENCE_DIR}"

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

command_string="openhands"
for arg in "$@"; do
  command_string+=" $(printf '%q' "${arg}")"
done

pull_args=()
if [[ "${IMAGE}" != *":local" ]]; then
  pull_args=(--pull=always)
fi

docker_cmd=(docker run --rm -i)
if [[ ${#pull_args[@]} -gt 0 ]]; then
  docker_cmd+=("${pull_args[@]}")
fi

# Docker run flags must come BEFORE the image name
if [[ "${OPENHANDS_ADD_HOST_GATEWAY:-0}" == "1" ]]; then
  docker_cmd+=("--add-host=host.docker.internal:host-gateway")
fi

docker_cmd+=(
  --name "${CONTAINER_NAME}"
  --label com.agentic-pr.role=openhands-cli
  --label com.agentic-pr.managed=true
  --memory "${CLI_MEMORY}"
  --memory-swap "${CLI_MEMORY_SWAP}"
  -e LOG_ALL_EVENTS=true
  -e LLM_MODEL="${LLM_MODEL_VALUE}"
  -e LLM_BASE_URL="${LLM_BASE_URL_VALUE}"
  -e LLM_API_KEY="${LLM_API_KEY_VALUE}"
  -e SANDBOX_USER_ID="$(id -u)"
  -e SANDBOX_VOLUMES="${REPO_PATH}:/workspace:rw"
  -e OH_PERSISTENCE_DIR=/.openhands
  -e OH_CONVERSATIONS_PATH=/workspace/.openhands-runtime/conversations
  -e OH_BASH_EVENTS_DIR=/workspace/.openhands-runtime/bash_events
  -e OH_AGENT_SERVER_ENV='{"LLM_MODEL": "ollama/qwen3-coder:30b", "LLM_BASE_URL": "http://host.docker.internal:11434/v1", "LLM_API_KEY": "local-llm", "OH_CONVERSATIONS_PATH": "/workspace/.openhands-runtime/conversations", "OH_BASH_EVENTS_DIR": "/workspace/.openhands-runtime/bash_events", "SANDBOX_USER_ID": "0", "SANDBOX_GROUP_ID": "0"}'
  -v /var/run/docker.sock:/var/run/docker.sock
  -v "${PERSISTENCE_DIR}:/.openhands"
  -v "${REPO_PATH}:/workspace"
  --workdir /workspace
  "${IMAGE}" "${command_string}"
)

exec "${docker_cmd[@]}"