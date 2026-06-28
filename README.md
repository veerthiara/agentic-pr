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

## PR Follow-up (Rev 08)

Rev 08 adds iterative PR repair from PR comments. After the agent creates a PR, you can review it and comment with `/agent <command>` to have the agent make additional changes to the same PR branch.

### How it works

1. You add a comment on an open PR starting with `/agent` (configurable via `PR_FOLLOWUP_COMMAND_PREFIX`)
2. The poller picks up the comment on its next cycle
3. The agent checks out the existing PR branch
4. Runs Aider with a follow-up prompt that includes the PR context and your command
5. If changes are made, commits and pushes to the same PR branch
6. Comments on the PR with the commit SHA

### Config

```env
ENABLE_PR_FOLLOWUPS=true
PR_FOLLOWUP_COMMAND_PREFIX=/agent
PR_FOLLOWUP_REQUIRE_LABEL=false
LABEL_FOLLOWUP=agent-followup
LABEL_FOLLOWUP_RUNNING=agent-followup-running
LABEL_FOLLOWUP_DONE=agent-followup-done
LABEL_FOLLOWUP_FAILED=agent-followup-failed
COMMENT_STATE_DIR=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/comment-state
MAX_FOLLOWUP_COMMENTS_PER_CYCLE=1
```

### Labels

- `agent-followup` - PR has a follow-up command for the agent
- `agent-followup-running` - Agent is processing a follow-up command
- `agent-followup-done` - Agent completed a follow-up command
- `agent-followup-failed` - Agent failed while processing a follow-up

### Running manually

```sh
make run-followup-once CONFIG=config/agent-test.env
```

Or let the poller handle it automatically:

```sh
make poll CONFIG=config/agent-test.env
```

### Comment state tracking

Processed comment IDs are stored locally under `var/comment-state/` so the same comment is never processed twice. One JSON file per repo/PR.

### Example PR comment

```
/agent add one small test for this change and update README if needed
```

### What the agent does

- Does NOT create a new branch
- Does NOT create a new PR
- Does NOT auto-merge
- Makes minimal additional changes to address the follow-up command
- Preserves existing PR intent
- Adds/updates tests when appropriate
- Updates README/docs when behavior changes

### Troubleshooting

- Check `var/comment-state/` to see which comments have been processed
- Check `var/runs/` for follow-up run records (run_type: "pr_followup")
- If a follow-up fails, the PR gets `agent-followup-failed` label and a comment with the error
- Full logs stay local under `logs/`

### Rev 08 acceptance test

Prerequisites:
- There is an open PR created by the agent
- Service is running or poller is running

Manual test:
1. On the open PR, add this comment:
   ```
   /agent add one small test for this change and update README if needed
   ```
2. If testing manually, run:
   ```sh
   make run-followup-once CONFIG=config/agent-test.env
   ```
3. Expected:
   - PR gets an accepted/started comment
   - Mac Studio checks out the PR branch
   - Aider runs
   - If changes are made, a new commit is pushed to the same PR
   - PR gets success comment with commit SHA
   - var/runs has a pr_followup run record
   - var/comment-state records the processed comment ID

## CI-Aware PR Follow-up (Rev 09)

Rev 09 adds CI/check awareness for PR follow-up repairs. The agent can now respond to PR comments like `/agent fix-ci` by gathering GitHub check/CI status and failed log context, adding that CI context to the Aider prompt, and pushing a follow-up commit to the same PR branch.

### Supported Commands

- `/agent fix-ci`
- `/agent fix checks`
- `/agent fix failing tests`

### How it works

1. You add a comment on an open PR starting with one of the CI command aliases
2. The poller picks up the comment on its next cycle (or run manually with `make run-followup-once`)
3. The agent collects CI context:
   - Lists all GitHub checks for the PR using `gh pr checks`
   - Identifies failing checks
   - Fetches log excerpts from failed workflow runs using `gh run view --log-failed`
   - Respects `CI_LOG_MAX_LINES` and `CI_LOG_MAX_BYTES` limits
4. Comments on PR that CI context is being collected
5. Runs optional planner stage with CI context
6. Runs Aider with CI-aware prompt including:
   - Failed check names
   - Log excerpts from failing checks
   - Instructions to fix root cause, prefer minimal changes
   - Do not remove tests just to make CI pass
   - Do not weaken assertions unless clearly correct
   - Preserve PR's existing intent
7. If changes are made and safety checks pass, commits and pushes to same PR branch
8. PR gets success comment with commit SHA
9. Run record saved with CI fields under `var/runs/`
10. Comment state recorded under `var/comment-state/`

### Config

```env
ENABLE_CI_CONTEXT=true
CI_COMMAND_ALIASES=/agent fix-ci,/agent fix checks,/agent fix failing tests
CI_LOG_MAX_LINES=250
CI_LOG_MAX_BYTES=40000
CI_INCLUDE_SUCCESSFUL_CHECKS=false
CI_REQUIRE_FAILED_CHECKS=false
ENABLE_REPO_INSTRUCTIONS=true
REPO_INSTRUCTIONS_DIR=.agentic-pr
REPO_INSTRUCTIONS_MAX_BYTES=40000
```

### Labels

Uses the same follow-up labels from Rev 08:
- `agent-followup` - PR has a follow-up command for the agent
- `agent-followup-running` - Agent is processing a follow-up command
- `agent-followup-done` - Agent completed a follow-up command
- `agent-followup-failed` - Agent failed while processing a follow-up

### Running manually

```sh
make run-followup-once CONFIG=config/agent-test.env
```

Or let the poller handle it automatically:

```sh
make poll CONFIG=config/agent-test.env
```

### CI Summary Command

To inspect CI status without running Aider:

```sh
make ci-summary CONFIG=config/agent-test.env PR=15
```

Or directly:

```sh
PYTHONPATH=src python3 -m agentic_pr.cli ci-summary --config config/agent-test.env --pr 15
```

### Run Record CI Fields

Rev 09 adds these fields to run records for CI follow-ups:
- `is_ci_fix` - Whether this was a CI fix run
- `ci_checks_found` - Whether any checks were found
- `ci_failing_checks_found` - Whether failing checks were found
- `ci_failed_check_names` - List of failed check names
- `ci_context_summary` - Summary of CI context
- `ci_log_excerpt` - Log excerpt (truncated)
- `ci_log_excerpt_file` - Path to full log excerpt file if large
- `ci_warnings` - Any warnings during CI context collection

Large log excerpts are saved to `var/run/<run_id>-ci-context.md`

### Example PR comment

```
/agent fix-ci
```

### What the agent does

- Does NOT create a new branch
- Does NOT create a new PR
- Does NOT auto-merge
- Collects CI context before running
- Makes minimal additional changes to address failing checks
- Preserves existing PR intent
- Adds/updates tests when appropriate
- Updates README/docs when behavior changes
- Does not remove tests just to make CI pass
- Does not weaken assertions unless clearly correct

### Fallback behavior

If no GitHub checks exist for the PR:
- If `CI_REQUIRE_FAILED_CHECKS=true`: Comments that no failing checks found, marks comment processed, does not run Aider
- If `CI_REQUIRE_FAILED_CHECKS=false`: Comments that no checks found, continues with warning in prompt

If logs cannot be fetched:
- Continues with available context
- Adds warning to prompt and run record

### Limitations (Rev 09)

- Only manually triggered by PR comment commands
- Does not automatically retry failed CI
- Does not auto-merge PRs
- If no GitHub Actions/checks exist, may continue with warning
- Log fetching depends on `gh` CLI capabilities

### Rev 09 acceptance test

Prerequisites:
- There is an open PR
- Ideally the PR has a failing GitHub Actions check
- Service is running or manual command can be used

Manual test:
1. On an open PR, add this PR comment:
   ```
   /agent fix-ci
   ```
2. If testing manually, run:
   ```sh
   make run-followup-once CONFIG=config/agent-test.env
   ```
3. Expected:
   - PR gets a comment that CI context is being collected
   - CI context is saved under var/run if available
   - Aider runs with CI context
   - If changes are made and safety checks pass, a new commit is pushed to the same PR branch
   - PR gets a success comment with commit SHA
   - var/runs has a pr_followup run record with CI fields
   - var/comment-state records the processed comment ID

Fallback test when no CI exists:
1. Comment:
   ```
   /agent fix-ci
   ```
2. Run:
   ```sh
   make run-followup-once CONFIG=config/agent-test.env
   ```
3. Expected:
   - It should not crash
   - It should comment that no failing checks/logs were found or that it is continuing with no CI context

---

## Rev 12: Multi-Repo Config Registry

### Why Multi-Repo Configs?

As you manage more repositories with the agent, you need a clean way to organize config files per repo without hard-coding engine or poller logic. Rev 12 introduces a `config/repos/` directory where each repo gets its own `.env` file.

### New Config Layout

```
config/
├── agent-test.env              # Legacy (still works)
├── repos/
│   ├── agent-test.env          # Primary config for agent-test repo
│   └── another-repo.env        # Add more repos here
└── repos.example/
    └── repo.env.example        # Template with all options
```

### How to List Configs

```sh
make list-configs
```

Output:
```
agent-test | veerthiara/agent-test-local-ai | /Users/.../agent-test | main | enabled
```

### How to Validate All Configs

```sh
make doctor-all
```

Runs `doctor` checks for each enabled config in `config/repos/` and prints compact results.

### How to Check Health of All Configs

```sh
make health-all
```

Runs health checks (GitHub, Ollama, Aider, launchd, lock file) for each enabled config.

### How to Run One Repo by Config Path

Both old and new paths work (backward compatible):

```sh
# Legacy path (still works)
make doctor CONFIG=config/agent-test.env

# New path
make doctor CONFIG=config/repos/agent-test.env
```

### How to Add a New Repo

1. Copy the example:
   ```sh
   cp config/repos.example/repo.env.example config/repos/my-new-repo.env
   ```
2. Edit `config/repos/my-new-repo.env` with your repo's values.
3. Ensure each repo has **separate directories** for:
   - `LOG_DIR`
   - `RUN_DIR`
   - `RUN_RECORD_DIR`
   - `LOCK_FILE`
   - `COMMENT_STATE_DIR`
   
   Or use shared folders with repo-safe filenames (e.g., `var/runs/my-repo/`).

4. Test it:
   ```sh
   make doctor CONFIG=config/repos/my-new-repo.env
   ```

### Launchd Service Per Repo

Rev 12 does **not** enable launchd services per repo by default. Each repo would need its own `SERVICE_LABEL` and separate `install-service` call. This is left for future revisions.

### Config Path Helper

Get the resolved config path for a repo name:

```sh
make config-path REPO=agent-test
# Output: /Users/.../agentic-pr/config/repos/agent-test.env
```

---

## Rev 13: Coding Engine Abstraction

### Why Engine Abstraction?

The agent now uses a clean `CodingEngine` interface so future engines (e.g. OpenHands) can be swapped in without rewriting the orchestrator, safety checks, planner, or GitHub logic.

### Current Supported Engine

| Engine | Status |
|--------|--------|
| `aider` | ✅ Implemented |
| `openhands` | ⚠️ Experimental |

### Config Key

```env
ENGINE=aider
ENGINE_TIMEOUT_SECONDS=1800
```

If `ENGINE_TIMEOUT_SECONDS` is not set, it falls back to `AIDER_TIMEOUT_SECONDS` (default 1800).

### How to Verify Engine Status

```sh
# Doctor shows engine availability
make doctor CONFIG=config/agent-test.env
# Output includes: ok: engine aider available

# Health shows engine status
make health CONFIG=config/agent-test.env
# Output includes: engine_aider: ok - aider available
```

### Architecture

```
get_engine(config)  →  AiderEngine  →  run(EngineRequest)  →  EngineResult
                          ↓
                     engine.doctor(config)  →  EngineDoctorResult
```

- `EngineRequest`: run_id, repo_path, prompt_file, prompt_text, model, log_file, timeout, mode
- `EngineResult`: engine_name, ok, exit_code, timed_out, log_file, error_summary
- New engines implement `CodingEngine` from `src/agentic_pr/engines/base.py`

---

## Rev 14: Experimental OpenHands Engine

OpenHands is now available as an optional experimental engine behind the Rev 13 engine abstraction. Aider is still the default and still the recommended path for normal service use.

### OpenHands Config

Keep your stable repo config on Aider:

```env
ENGINE=aider
```

Use the experimental config when you want to try OpenHands:

```sh
config/repos/agent-test-openhands.env
```

Key settings:

```env
ENGINE=openhands
ENGINE_TIMEOUT_SECONDS=3600
OPENHANDS_COMMAND=/Users/vsinghthiara/Developer/Learning/agentic-pr/infra/openhands/run-openhands.sh
OPENHANDS_TIMEOUT_SECONDS=3600
OPENHANDS_EXTRA_ARGS=
OPENHANDS_USE_JSON_OUTPUT=false
OPENHANDS_EXPERIMENTAL=true
OPENHANDS_LLM_BASE_URL=http://host.docker.internal:11434/v1
OPENHANDS_API_KEY=local-llm
OPENHANDS_DOCKER_IMAGE=agentic-pr/openhands-cli:local
```

### Containerized OpenHands

The repo now includes a local Docker-based OpenHands CLI path under:

```sh
infra/openhands/
```

Files there:

- `Dockerfile` builds a local CLI image with `openhands`
- `run-openhands.sh` runs the CLI image against the host Docker socket and your repo workspace
- `docker-compose.yml` gives you a compose-based entrypoint for manual experimentation
- `.env.example` shows the expected environment values

This keeps OpenHands out of your global Python environment. The wrapper builds the local image on first use if it does not already exist.

### Run OpenHands Locally

If you want to run OpenHands directly, outside the GitHub issue loop, use this order.

1. Start the local container runtime:

```sh
colima start
docker ps
```

Expected:
- `colima start` finishes without error
- `docker ps` prints an empty table or running containers

2. Verify Ollama is up and your model exists:

```sh
ollama list
```

Expected:
- you can see `qwen3-coder:30b`

3. Smoke-test the local OpenHands wrapper:

```sh
infra/openhands/run-openhands.sh --version
```

Expected:
- the wrapper builds the local image on first run if needed
- you see an OpenHands CLI version line

4. Run a direct headless OpenHands task against your local test repo:

```sh
LLM_MODEL='openai/qwen3-coder:30b' \
LLM_BASE_URL='http://host.docker.internal:11434/v1' \
LLM_API_KEY='local-llm' \
OPENHANDS_REPO_PATH='/Users/vsinghthiara/Developer/Learning/agent-test' \
infra/openhands/run-openhands.sh \
  --headless \
  --override-with-envs \
  --task 'Reply with the single word done and make no file changes.'
```

Expected:
- OpenHands initializes the agent
- it prints progress
- it finishes with a short result

5. Run a real local coding task:

```sh
LLM_MODEL='openai/qwen3-coder:30b' \
LLM_BASE_URL='http://host.docker.internal:11434/v1' \
LLM_API_KEY='local-llm' \
OPENHANDS_REPO_PATH='/Users/vsinghthiara/Developer/Learning/agent-test' \
infra/openhands/run-openhands.sh \
  --headless \
  --override-with-envs \
  --task 'Add a max_value(a, b) helper to calc.py and add tests. Keep the change minimal.'
```

6. Inspect what changed in the local repo:

```sh
git -C /Users/vsinghthiara/Developer/Learning/agent-test status --short
git -C /Users/vsinghthiara/Developer/Learning/agent-test diff --stat
```

Use this direct path first when you want to debug OpenHands itself before involving GitHub issues, branching, PR creation, or the poller.

### How To Verify It

Stable Aider regression:

```sh
make test
make doctor CONFIG=config/repos/agent-test.env
make health CONFIG=config/repos/agent-test.env
```

Experimental OpenHands checks:

```sh
make doctor CONFIG=config/repos/agent-test-openhands.env
make health CONFIG=config/repos/agent-test-openhands.env
```

Expected:

- `doctor` reports the configured OpenHands wrapper as available
- `health` shows:
  - `Engine: openhands`
  - `Engine status: ok`
  - `Experimental: true`

If the container runtime is not available yet, doctor fails clearly and health shows:

- `Engine: openhands`
- `Engine status: fail`
- `Experimental: true`

### Manual OpenHands Issue Test

Do this only after `make doctor CONFIG=config/repos/agent-test-openhands.env` passes:

1. Make sure the background Aider poller is not running if you want a clean manual OpenHands test.
2. Create a GitHub issue with label `agent-run`
3. Run:

```sh
make run-once CONFIG=config/repos/agent-test-openhands.env
```

4. Check the issue comments in GitHub.
5. Check the local run log and run record:

```sh
ls -lt logs | head
ls -lt var/runs | head
```

6. If successful, inspect the created PR in GitHub.

Suggested test issue:

Title:
`Agent test OpenHands: add mode function`

Body:
`Edit calc.py to add a mode(values) function that returns the most common value. Keep it simple. Follow repo instructions and add tests if tests exist.`

What you should expect from a successful issue run:

- issue gets a start comment
- planner comment appears
- implementation comment appears
- a PR-created comment appears
- `var/runs/run-*.json` contains the engine metadata
- `logs/run-*.log` contains the OpenHands session output

### Switching Back To Aider

Go back to the stable config at any time:

```sh
make run-once CONFIG=config/repos/agent-test.env
make poll CONFIG=config/repos/agent-test.env
```

Do not install the OpenHands launchd service flow until manual OpenHands runs are working on your machine. OpenHands may need its own installation or local settings before the experimental config can pass doctor.
