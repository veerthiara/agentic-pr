# agentic-pr

Local GitHub issue runner for an Aider + Ollama workflow.

Rev 03 adds a polling loop while keeping `make` as the entrypoint. GitHub operations still go through the `gh` CLI, and code generation still runs Aider as an external command.

## Requirements

- Python 3.11+
- `git`
- `gh`, authenticated against the target repository
- `aider`
- Ollama running the configured model

## Setup

Edit `config/agent-test.env` if needed. The current test config points at:

```env
REPO_PATH=/Users/vsinghthiara/Developer/Learning/agent-test
OWNER_REPO=veerthiara/agent-test-local-ai
```

Then check the local environment:

```sh
make doctor CONFIG=config/agent-test.env
```

Create the GitHub labels if needed:

```sh
make ensure-labels CONFIG=config/agent-test.env
```

## Run Once

Create or pick a GitHub issue, add the `agent-run` label, then run:

```sh
make run-once CONFIG=config/agent-test.env
```

Expected flow:

1. Find one open issue with `agent-run`.
2. Move it to `agent-running`.
3. Update the base branch and create `agent/issue-<number>-<timestamp>`.
4. Run Aider with the configured Ollama model.
5. Commit with a `REV03:` commit message and push the branch.
6. Open a PR.
7. Comment on the issue with the PR URL.
8. Replace `agent-running` with `agent-pr-created`.

## Polling

Rev 03 lets the Mac Studio wait for GitHub issues and process one issue per poll cycle.

Start the poller:

```sh
make poll CONFIG=config/agent-test.env
```

Stop it with `Ctrl+C`.

The poller:

1. Prints the repo, owner repo, polling interval, model, and lock file on startup.
2. Sleeps for `POLL_INTERVAL_SECONDS` between cycles.
3. Calls the same `run-once` workflow each cycle.
4. Processes only one issue per cycle.
5. Uses `LOCK_FILE` to avoid overlapping runs.
6. Continues polling after a failed issue.

To test from GitHub mobile or browser, create an issue in `veerthiara/agent-test-local-ai` and apply the `agent-run` label. The expected label flow is:

```text
agent-run -> agent-running -> agent-pr-created
```

If the run fails after an issue is picked up, the issue should receive `agent-failed`.

Logs are written to:

```text
/Users/vsinghthiara/Developer/Learning/agentic-pr/logs
```

Rev 04 will add a macOS `launchd` service so this can start automatically.

## LaunchAgent Service

Rev 04 adds a macOS user LaunchAgent for the poller. It runs as your normal user after login, so it can use your existing `gh` authentication and local Aider/Ollama setup. It does not use `sudo`, does not auto-merge PRs, and still calls the Python CLI as the real runner.

Install the service:

```sh
make install-service CONFIG=config/agent-test.env
```

Start or restart it:

```sh
make start-service
make restart-service
```

Stop it:

```sh
make stop-service
```

Check status:

```sh
make status-service
```

Follow logs:

```sh
make tail-service-logs
```

The service writes launchd output to:

```text
logs/launchd.out.log
logs/launchd.err.log
```

To test from GitHub mobile or browser, create an issue in `veerthiara/agent-test-local-ai` and apply the `agent-run` label. The service should pick it up, run the same poller workflow, and create a PR.

Because this project lives under `Documents`, macOS privacy permissions may block background access. If that happens, `logs/launchd.err.log` should reveal the permission failure, and a later revision can move the project to `~/Developer`.

Uninstall without deleting logs:

```sh
make uninstall-service
```

## Test

```sh
make test
```

The tests cover local Python helpers and do not call GitHub, Aider, or Ollama.
