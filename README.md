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

## GitHub Observability

Rev 05 makes each picked-up issue explain itself from GitHub.

When the agent starts work, it now creates a run ID like:

```text
run-YYYYMMDD-HHMMSS-issue-<issue_number>
```

That run ID appears in issue comments, the PR body, local log filenames, and local JSON records.

Status labels used by the agent:

```text
agent-run
agent-running
agent-pr-created
agent-failed
agent-no-changes
agent-blocked
```

Run records are written locally to:

```text
/Users/vsinghthiara/Developer/Learning/agentic-pr/var/runs
```

Useful local commands:

```sh
make list-runs CONFIG=config/agent-test.env
make show-last-run CONFIG=config/agent-test.env
```

The issue receives short comments for:

1. Agent started.
2. Aider is about to run with the local Ollama model.
3. PR created.
4. No file changes produced.
5. Failure, including stage and short error summary.

The comments intentionally do not paste full logs into GitHub. Full logs stay local under `logs/`.

The PR body includes the linked issue, run ID, model, base branch, agent branch, host label, validation reminder, no-auto-merge note, and local log path.

Rev 05 acceptance test:

```sh
make test
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make status-service
```

Then create a GitHub issue in `veerthiara/agent-test-local-ai` with label `agent-run`.

Title:

```text
Agent test: add min function
```

Body:

```text
Edit calc.py to add a min_value(a, b) function that returns the smaller value. Keep it simple.
```

After the service picks it up, confirm GitHub issue comments, PR metadata, and a local JSON file in `var/runs/`.

## Safety Guardrails

Rev 06 adds guardrails before using the agent on real repositories.

The agent now blocks a run before commit, push, or PR creation when:

- A changed file matches `BLOCKED_PATH_PATTERNS`.
- Changed file count exceeds `MAX_CHANGED_FILES`.
- Diff line count exceeds `MAX_DIFF_LINES`.
- `.aiderignore` is required but missing.
- Aider exceeds `AIDER_TIMEOUT_SECONDS`.
- Optional `LINT_CMD` or `TEST_CMD` fails.

Blocked runs receive the `agent-blocked` label and a short GitHub issue comment with the run ID and reason. Failed runs receive `agent-failed`. Full logs stay local.

Relevant config:

```env
AIDER_TIMEOUT_SECONDS=1800
MAX_CHANGED_FILES=20
MAX_DIFF_LINES=800
REQUIRE_AIDERIGNORE=true
BLOCKED_PATH_PATTERNS=.env,.env.*,*.pem,*.key,*.p12,*.pfx,secrets/*,credentials/*,node_modules/*,.venv/*,dist/*,build/*,**pycache**/*
TEST_CMD=
LINT_CMD=
STALE_LOCK_SECONDS=7200
```

Use `TEST_CMD` and `LINT_CMD` for repository-specific validation. For Rev 06, validation failure prevents pushing and PR creation.

Stale locks older than `STALE_LOCK_SECONDS` are removed automatically. Active locks still prevent duplicate runs.

Before testing Rev 06, create `/Users/vsinghthiara/Developer/Learning/agent-test/.aiderignore` with the blocked path list above.

## Planner Stage

Rev 07 adds a planner and repo-context stage before Aider runs. This helps broader tasks where the agent needs to understand the repo shape, identify files to modify or create, and produce a concrete implementation plan.

Planner flow:

```text
issue -> repo context -> local Ollama planner -> concise GitHub plan comment -> planner-enhanced Aider prompt
```

Config:

```env
ENABLE_PLANNER=true
PLANNER_MODEL=ollama/qwen3-coder:30b
REPO_CONTEXT_MAX_FILES=80
REPO_CONTEXT_MAX_BYTES=120000
PLANNER_TIMEOUT_SECONDS=900
COMMENT_PLAN=true
```

Set `ENABLE_PLANNER=false` to return to the raw issue-to-Aider behavior. Tune `REPO_CONTEXT_MAX_FILES` and `REPO_CONTEXT_MAX_BYTES` if the planner needs more or less context.

Planner output is stored locally under:

```text
var/run/<run_id>-planner.md
```

GitHub issue comments stay short. You should see comments for planner started/completed, planner failed with fallback, and implementation started.

The run record in `var/runs/` now includes planner status, planner output path, plan summary, planned files to modify/create, and planned test plan.
