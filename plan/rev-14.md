# Rev 14: Experimental OpenHands Engine

## Goal

Add OpenHands as an optional experimental coding engine behind the Rev 13 engine abstraction while keeping `ENGINE=aider` as the stable default.

## Files Changed

### New Files
- `src/agentic_pr/engines/openhands_engine.py` - Experimental OpenHands engine runner and doctor checks
- `config/repos/agent-test-openhands.env` - Experimental OpenHands repo config
- `tests/test_openhands_engine.py` - OpenHands engine unit tests
- `plan/rev-14.md` - This document

### Updated Files
- `src/agentic_pr/config.py`
- `src/agentic_pr/engine.py`
- `src/agentic_pr/engines/__init__.py`
- `src/agentic_pr/doctor.py`
- `src/agentic_pr/health.py`
- `src/agentic_pr/orchestrator.py`
- `src/agentic_pr/status.py`
- `src/agentic_pr/cli.py`
- `Makefile`
- `README.md`
- `config/agent-test.env`
- `config/agent-test.env.example`
- `config/repos/agent-test.env`
- `config/repos.example/repo.env.example`
- `tests/test_config.py`
- `tests/test_engine.py`
- `tests/test_health.py`
- `tests/test_run_history.py`
- `tests/test_run_record.py`
- `tests/test_status.py`

## Config Changes

Added OpenHands-specific settings:

```env
OPENHANDS_COMMAND=openhands
OPENHANDS_TIMEOUT_SECONDS=3600
OPENHANDS_EXTRA_ARGS=
OPENHANDS_USE_JSON_OUTPUT=false
OPENHANDS_EXPERIMENTAL=false
```

Experimental repo config:

```env
config/repos/agent-test-openhands.env
```

Important values there:

```env
ENGINE=openhands
OPENHANDS_EXPERIMENTAL=true
LOCK_FILE=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test-openhands.lock
```

## Commands

Stable Aider path:

```sh
make test
make doctor CONFIG=config/repos/agent-test.env
make health CONFIG=config/repos/agent-test.env
```

Experimental OpenHands path:

```sh
make doctor CONFIG=config/repos/agent-test-openhands.env
make health CONFIG=config/repos/agent-test-openhands.env
make run-once CONFIG=config/repos/agent-test-openhands.env
```

Optional helper:

```sh
make engine-doctor CONFIG=config/repos/agent-test-openhands.env
```

## Manual Test Steps

### A. Stable Aider Regression
1. `make test`
2. `make doctor CONFIG=config/repos/agent-test.env`
3. `make health CONFIG=config/repos/agent-test.env`

Expected:
- tests pass
- Aider doctor passes
- health shows `Engine: aider`

### B. OpenHands Doctor Check
1. `make doctor CONFIG=config/repos/agent-test-openhands.env`
2. `make health CONFIG=config/repos/agent-test-openhands.env`

Expected:
- if OpenHands is installed, doctor and health report engine ok
- if OpenHands is missing, doctor fails clearly and health shows `engine_openhands: fail`

### C. Manual OpenHands Issue Run
Create GitHub issue:

Title:
`Agent test OpenHands: add mode function`

Body:
`Edit calc.py to add a mode(values) function that returns the most common value. Keep it simple. Follow repo instructions and add tests if tests exist.`

Label:
`agent-run`

Run:

```sh
make run-once CONFIG=config/repos/agent-test-openhands.env
```

Expected:
- OpenHands only edits files in the checked out local branch
- orchestrator still handles commit, push, PR creation, labels, and comments
- run record includes `engine=openhands`

### D. PR Follow-up After C Works

Comment on the PR:

```text
/agent update README if needed and keep the change minimal
```

Run:

```sh
make run-followup-once CONFIG=config/repos/agent-test-openhands.env
```

## Rollback Notes

- Delete `src/agentic_pr/engines/openhands_engine.py`
- Delete `config/repos/agent-test-openhands.env`
- Delete `tests/test_openhands_engine.py`
- Revert engine-related changes in config, doctor, health, orchestrator, status, CLI, README, and tests
- Switch back to `ENGINE=aider`

## Known Limitations

- OpenHands is not installed by default on this machine
- The CLI shape varies by release, so the runner probes `openhands --help` and uses a defensive command builder
- JSON mode is optional and only enabled when configured
- OpenHands is not recommended for background service use until manual issue tests pass

## Acceptance Criteria

- `ENGINE=aider` still works without behavior changes
- `ENGINE=openhands` returns `OpenHandsEngine`
- doctor/health report missing OpenHands clearly without breaking Aider
- orchestrator stores engine exit metadata in run records
- issue comments and PR body show engine-aware wording
- unit tests do not require real OpenHands, GitHub, Ollama, or network calls

## Commit Boundary Note

Rev 14 must remain a separate revision from Rev 13.
If committed later, use:

```text
REV14: add experimental OpenHands engine
```
