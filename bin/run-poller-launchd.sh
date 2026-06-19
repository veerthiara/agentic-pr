#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="${1:-$PROJECT_ROOT/config/agent-test.env}"

export PYTHONPATH="$PROJECT_ROOT/src"
export PYTHONUNBUFFERED=1
export PATH="/Users/vsinghthiara/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/vsinghthiara/Library/Python/3.9/bin"

cd "$PROJECT_ROOT"

echo "launchd poller startup"
date
echo "user: $(whoami)"
echo "pwd: $(pwd)"
echo "config: $CONFIG_PATH"

echo "python3 path: $(command -v python3 || true)"
python3 --version

echo "gh path: $(command -v gh || true)"
gh --version

if command -v aider >/dev/null 2>&1; then
  echo "aider path: $(command -v aider)"
  aider --version || true
else
  echo "aider path: not found"
fi

if command -v ollama >/dev/null 2>&1; then
  echo "ollama path: $(command -v ollama)"
  ollama --version || true
else
  echo "ollama path: not found"
fi

exec python3 -m agentic_pr.cli poll --config "$CONFIG_PATH"
