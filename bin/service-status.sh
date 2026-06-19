#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_LABEL="com.veer.agentic-pr.agent-test"
DOMAIN="gui/$(id -u)"
OUT_LOG="$PROJECT_ROOT/logs/launchd.out.log"
ERR_LOG="$PROJECT_ROOT/logs/launchd.err.log"

if launchctl print "$DOMAIN/$SERVICE_LABEL"; then
  true
else
  echo "Service is not loaded: $SERVICE_LABEL"
  echo "Install it with: make install-service CONFIG=config/agent-test.env"
fi

echo
echo "Disabled state:"
launchctl print-disabled "$DOMAIN" | grep "$SERVICE_LABEL" || echo "No disabled-state entry for $SERVICE_LABEL"

echo
echo "Last 40 lines of $OUT_LOG"
if [ -f "$OUT_LOG" ]; then
  tail -n 40 "$OUT_LOG"
else
  echo "No stdout log yet."
fi

echo
echo "Last 40 lines of $ERR_LOG"
if [ -f "$ERR_LOG" ]; then
  tail -n 40 "$ERR_LOG"
else
  echo "No stderr log yet."
fi
