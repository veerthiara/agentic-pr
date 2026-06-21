# Rev 11: Run History, Service Health, and Cleanup

## Problem
The agent now has many moving parts and artifacts:
- launchd service
- poller
- issue runs
- PR follow-up runs
- CI-aware runs
- planner output
- prompt files
- logs
- JSON run records
- comment-state files
- lock files

Operators need quick answers to:
- Is the service healthy?
- What did the agent do recently?
- Which runs failed?
- What issue/PR did a run belong to?
- Where is the log for a run?
- Can I clean old logs/prompts/run files safely?

## Solution
Add a maintenance/operator layer without changing the main agent behavior.

## Implementation

### Configuration Values
Added to `config/agent-test.env` and `config/agent-test.env.example`:
```
RUN_RETENTION_DAYS=30
LOG_RETENTION_DAYS=30
PROMPT_RETENTION_DAYS=30
COMMENT_STATE_RETENTION_DAYS=90
MAX_LOG_PREVIEW_LINES=80
SERVICE_LABEL=com.veer.agentic-pr.agent-test
```

### New Modules

#### `src/agentic_pr/run_history.py`
- Read run records from RUN_RECORD_DIR
- Sort runs by started_at or file mtime newest first
- Provide: `list_runs(config, limit=20)`, `get_run(config, run_id)`, `get_last_run(config)`
- Handle missing/invalid JSON gracefully
- Do not crash if var/runs is empty
- Include run type, status, issue/pr number, branch, PR URL, model, started_at, finished_at, error summary

#### `src/agentic_pr/health.py`
- Build a health summary without running Aider
- Check: config loads, REPO_PATH exists, REPO_PATH is git repo, working tree status, gh exists, gh auth status works, OWNER_REPO is accessible if possible, Ollama API responds, aider exists, LaunchAgent status using SERVICE_LABEL if on macOS, lock file status (missing, active, stale), latest run status
- Provide CLI-friendly structured output
- Should not fail the entire command because one optional check fails; collect statuses and return an overall ok/warn/fail

#### `src/agentic_pr/maintenance.py`
- Cleanup old artifacts safely
- Support dry-run mode
- Use retention values from config: RUN_RETENTION_DAYS for var/runs/*.json, LOG_RETENTION_DAYS for logs/*.log, PROMPT_RETENTION_DAYS for var/run/*prompt.md, *planner.md, *ci-context.md, COMMENT_STATE_RETENTION_DAYS for var/comment-state/*.json
- Never delete: source files, config files, README, plan files, launchd files, active lock file unless it is stale
- Provide: `plan_cleanup(config) -> list[CleanupItem]`, `run_cleanup(config, dry_run=True)`
- CleanupItem should include path, reason, age_days, category

### CLI Updates
Updated `src/agentic_pr/cli.py` with new commands:
- `python -m agentic_pr.cli health --config config/agent-test.env`
- `python -m agentic_pr.cli list-runs --config config/agent-test.env --limit 20`
- `python -m agentic_pr.cli show-last-run --config config/agent-test.env`
- `python -m agentic_pr.cli show-run --config config/agent-test.env --run-id <run_id>`
- `python -m agentic_pr.cli cleanup --config config/agent-test.env --dry-run`
- `python -m agentic_pr.cli cleanup --config config/agent-test.env --apply`

### Makefile Updates
Added targets to `Makefile`:
```
health:
	python -m agentic_pr.cli health --config $(CONFIG)

list-runs:
	python -m agentic_pr.cli list-runs --config $(CONFIG)

show-last-run:
	python -m agentic_pr.cli show-last-run --config $(CONFIG)

show-run:
	python -m agentic_pr.cli show-run --config $(CONFIG) --run-id $(RUN_ID)

cleanup-dry-run:
	python -m agentic_pr.cli cleanup --config $(CONFIG) --dry-run

cleanup:
	python -m agentic_pr.cli cleanup --config $(CONFIG) --apply
```

### Tests
Added new test files:
- `tests/test_run_history.py`
- `tests/test_health.py` 
- `tests/test_maintenance.py`

Updated existing tests:
- `tests/test_config.py` - added test for new config fields

## Acceptance Test

1. Run:
```bash
make test
make doctor CONFIG=config/agent-test.env
make health CONFIG=config/agent-test.env
```
2. Run:
```bash
make list-runs CONFIG=config/agent-test.env
```
3. Run:
```bash
make show-last-run CONFIG=config/agent-test.env
```
4. Pick a run ID from list-runs and run:
```bash
make show-run CONFIG=config/agent-test.env RUN_ID=<run_id>
```
5. Run cleanup preview:
```bash
make cleanup-dry-run CONFIG=config/agent-test.env
```
6. Only after reviewing dry-run output:
```bash
make cleanup CONFIG=config/agent-test.env
```

Expected:
- tests pass
- health prints service/repo/github/ollama/aider status
- list-runs shows recent issue and PR follow-up runs
- show-last-run shows details and log path
- cleanup-dry-run lists old artifacts or says nothing to clean
- cleanup does not delete source/config/plan files