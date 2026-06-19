#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_LABEL="com.veer.agentic-pr.agent-test"
TEMPLATE_PATH="$PROJECT_ROOT/launchd/$SERVICE_LABEL.plist.template"
PLIST_PATH="$HOME/Library/LaunchAgents/$SERVICE_LABEL.plist"
CONFIG_PATH="${1:?Usage: bin/install-launchd.sh <config-path>}"
DOMAIN="gui/$(id -u)"

if [[ "$CONFIG_PATH" != /* ]]; then
  CONFIG_PATH="$PROJECT_ROOT/$CONFIG_PATH"
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$PROJECT_ROOT/logs"
: > "$PROJECT_ROOT/logs/launchd.out.log"
: > "$PROJECT_ROOT/logs/launchd.err.log"
chmod 755 "$PROJECT_ROOT/bin/run-poller-launchd.sh"

launchctl bootout "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true
launchctl bootout "$DOMAIN" "$PLIST_PATH" >/dev/null 2>&1 || true

python3 - "$TEMPLATE_PATH" "$PLIST_PATH" "$CONFIG_PATH" "$PROJECT_ROOT" <<'PYRENDER'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
plist_path = Path(sys.argv[2])
config_path = sys.argv[3]
project_root = sys.argv[4]

rendered = (
    template_path.read_text()
    .replace("__CONFIG_PATH__", config_path)
    .replace("__PROJECT_ROOT__", project_root)
)
plist_path.write_text(rendered)
PYRENDER

chmod 644 "$PLIST_PATH"
plutil -lint "$PLIST_PATH"

# Clear a stale disabled bit before bootstrap. If the prior stop-service
# disabled this label, launchctl may otherwise fail with error 5.
launchctl enable "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
launchctl enable "$DOMAIN/$SERVICE_LABEL"
launchctl kickstart -k "$DOMAIN/$SERVICE_LABEL"

echo "Installed $SERVICE_LABEL"
echo
echo "Next commands:"
echo "  make status-service"
echo "  make tail-service-logs"
