# Rev 13: Coding Engine Abstraction

## Goal
Introduce a clean engine interface while preserving current behavior with Aider, so that future engines (e.g. OpenHands) can be swapped in without rewriting the orchestrator, safety checks, planner, run records, or GitHub logic.

## Files Changed

### New Files
- `src/agentic_pr/engines/__init__.py` - Package exports
- `src/agentic_pr/engines/base.py` - Abstract `CodingEngine`, `EngineRequest`, `EngineResult`, `EngineDoctorResult`
- `src/agentic_pr/engines/aider_engine.py` - `AiderEngine` implementation
- `src/agentic_pr/engine.py` - `get_engine()` factory, `list_supported_engines()`
- `tests/test_engine.py` - 8 engine tests (all passing)
- `plan/rev-13.md` - This file

### Modified Files
- `config/agent-test.env` - Added `ENGINE=aider`, `ENGINE_TIMEOUT_SECONDS=1800`
- `config/repos/agent-test.env` - Added ENGINE config
- `config/agent-test.env.example` - Added ENGINE config
- `config/repos.example/repo.env.example` - Added ENGINE config
- `src/agentic_pr/config.py` - Added `engine`, `engine_timeout_seconds` fields
- `src/agentic_pr/orchestrator.py` - Uses `get_engine().run(EngineRequest)` instead of `run_aider()`
- `src/agentic_pr/doctor.py` - Reports engine availability
- `src/agentic_pr/health.py` - Reports engine status via `_check_engine()` using `engine.doctor(config)`
- `src/agentic_pr/run_record.py` - Added `engine`, `engine_exit_code`, `engine_timed_out`, `engine_error_summary` fields
- `src/agentic_pr/status.py` - Added Engine to PR body
- `tests/test_health.py` - Updated engine-aware health tests
- `tests/test_run_record.py` - Added engine field test

## Config Changes
- `ENGINE=aider` - Config key (default: aider)
- `ENGINE_TIMEOUT_SECONDS=1800` - Falls back to `AIDER_TIMEOUT_SECONDS` if not set

## Behavior Preserved
- Issue-to-PR flow unchanged
- PR follow-up flow unchanged
- CI fix flow unchanged
- Planner, safety, run records, launchd, multi-repo configs all unchanged
- Aider remains the only implemented engine

## Tests
- 8 new engine tests
- Engine tests mock external commands
- Run record tests verify engine fields on old and new records

## Acceptance Tests
1. `make test` - 8+ engine tests pass
2. `make doctor CONFIG=config/agent-test.env` - Shows `ok: engine aider available`
3. `make health CONFIG=config/agent-test.env` - Shows `engine_aider: ok - aider available`
4. Normal issue flow - Issue-to-PR still works, PR body includes `Engine: aider`
5. PR follow-up - `/agent fix-ci` still works, run records include `engine=aider`

## Rollback Notes
- Remove `src/agentic_pr/engines/`, `src/agentic_pr/engine.py`, `tests/test_engine.py`
- Revert `config.py`, `orchestrator.py`, `doctor.py`, `health.py`, `run_record.py`, `status.py`
- Remove ENGINE lines from config files
- Revert `tests/test_health.py`, `tests/test_run_record.py`

## Important Notes
- Rev 13 is a **separate commit** from Rev 12
- Does not add OpenHands or any new engine
- Does not change user-facing behavior
- `aider_runner.py` is kept as a backward-compatible wrapper
- All existing tests pass without modification