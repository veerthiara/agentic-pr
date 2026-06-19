#!/usr/bin/env bash
set -euo pipefail

SERVICE_LABEL="com.veer.agentic-pr.agent-test"
PLIST_PATH="$HOME/Library/LaunchAgents/$SERVICE_LABEL.plist"
DOMAIN="gui/$(id -u)"

launchctl disable "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true
launchctl kill TERM "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true

if [ -f "$PLIST_PATH" ]; then
  launchctl bootout "$DOMAIN" "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl bootout "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
  echo "Removed $PLIST_PATH"
else
  launchctl bootout "$DOMAIN/$SERVICE_LABEL" >/dev/null 2>&1 || true
  echo "LaunchAgent plist was not installed: $PLIST_PATH"
fi

echo "Logs were left in place."
