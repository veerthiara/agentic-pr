Rev 05 — GitHub-visible observability

Goal: make each agent run understandable from GitHub without SSH-ing into the Mac Studio.

Scope:

- Keep Aider as the coding engine.
- Keep GitHub operations through `gh`.
- Do not add Slack, Discord, Cloudflare, OpenHands, OpenClaw, Hermes, LangGraph, or auto-merge behavior.
- Add concise issue comments, richer status labels, run IDs, PR metadata, and local JSON run records.

Labels:

- `agent-run`
- `agent-running`
- `agent-pr-created`
- `agent-failed`
- `agent-no-changes`
- `agent-blocked`

Run IDs:

```text
run-YYYYMMDD-HHMMSS-issue-<issue_number>
```

Run records:

```text
var/runs/<run_id>.json
```

Commands:

```sh
make test
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make status-service
make list-runs CONFIG=config/agent-test.env
make show-last-run CONFIG=config/agent-test.env
```

Acceptance test:

1. Run `make test`.
2. Run `make doctor CONFIG=config/agent-test.env`.
3. Run `make ensure-labels CONFIG=config/agent-test.env`.
4. Run `make status-service`.
5. Create a GitHub issue in `veerthiara/agent-test-local-ai` with label `agent-run`.
6. Confirm the issue receives short status comments.
7. Confirm the PR body includes run ID, model, base branch, agent branch, host label, validation reminder, no-auto-merge note, and local log path.
8. Confirm `var/runs/` contains a JSON run record.

Test issue:

Title: `Agent test: add min function`

Body: `Edit calc.py to add a min_value(a, b) function that returns the smaller value. Keep it simple.`

Troubleshooting:

- Use `make show-last-run CONFIG=config/agent-test.env` for the newest local run record.
- Use `make tail-service-logs` for launchd stdout/stderr.
- GitHub comments intentionally stay short and do not include full logs.
