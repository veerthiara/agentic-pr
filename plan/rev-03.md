Rev 03 — Polling loop

Purpose: leave the Mac Studio running so GitHub issues labeled `agent-run` are picked up automatically and processed through the existing one-shot issue-to-PR workflow.

Scope:

- Keep Aider as the coding engine.
- Keep `gh` CLI for GitHub operations.
- Do not add webhooks, launchd, Slack, Discord, multi-repo routing, or auto-merge.
- Add a Python poller that calls the existing orchestrator once per cycle.

Commands:

```sh
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make poll CONFIG=config/agent-test.env
```

Config additions:

```env
POLL_INTERVAL_SECONDS=300
LOCK_FILE=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test.lock
```

Expected behavior:

1. Start the poller on the Mac Studio.
2. Create an issue from GitHub mobile/browser with label `agent-run`.
3. Poller runs one issue per cycle.
4. Lock file prevents overlapping runs.
5. Existing run-once flow creates branch, commit, push, and PR.
6. Poller logs results and keeps running after failures.

Manual acceptance test:

1. Run `make ensure-labels CONFIG=config/agent-test.env`.
2. Run `make poll CONFIG=config/agent-test.env`.
3. Create a GitHub issue labeled `agent-run`.
4. Confirm a PR appears.
5. Confirm issue moves through `agent-running` to `agent-pr-created`, or `agent-failed` if the run fails.
