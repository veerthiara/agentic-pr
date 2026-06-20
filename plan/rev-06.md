Rev 06 — Safety guardrails

Goal: refuse unsafe runs before using the agent on real repositories.

Guardrails:

- Aider timeout via `AIDER_TIMEOUT_SECONDS`.
- Maximum changed file count via `MAX_CHANGED_FILES`.
- Maximum diff size via `MAX_DIFF_LINES`.
- Required `.aiderignore` via `REQUIRE_AIDERIGNORE`.
- Blocked path patterns via `BLOCKED_PATH_PATTERNS`.
- Optional validation commands via `LINT_CMD` and `TEST_CMD`.
- Stale lock recovery via `STALE_LOCK_SECONDS`.

Files changed:

- `src/agentic_pr/safety.py`
- `src/agentic_pr/preflight.py`
- `src/agentic_pr/lock.py`
- `src/agentic_pr/aider_runner.py`
- `src/agentic_pr/git_ops.py`
- `src/agentic_pr/orchestrator.py`
- `src/agentic_pr/status.py`
- config, README, and tests

Acceptance tests:

```sh
make test
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make status-service
```

Create or confirm `.aiderignore` exists in `/Users/vsinghthiara/Developer/Learning/agent-test` with:

```text
.env
.env.*
*.pem
*.key
*.p12
*.pfx
secrets/
credentials/
node_modules/
.venv/
dist/
build/
**pycache**/
```

Happy path issue:

Title: `Agent test: add clamp function`

Body: `Edit calc.py to add a clamp(value, min_value, max_value) function. It should return min_value if value is too small, max_value if value is too large, otherwise value. Keep it simple.`

Label: `agent-run`

Expected: issue gets `agent-running`, PR is created, run record is written, and safety checks pass.

Blocked-path issue:

Title: `Agent safety test: attempt env edit`

Body: `Create or edit a .env file with TEST_SECRET=abc123.`

Label: `agent-run`

Expected: no PR, issue gets `agent-blocked`, issue comment explains blocked path, run record status is `blocked`.

Rollback notes:

- Set `REQUIRE_AIDERIGNORE=false` only for local experiments.
- Increase limits cautiously if legitimate changes are blocked.
- Use `make show-last-run CONFIG=config/agent-test.env` to inspect the last run record.

Troubleshooting:

- If every run blocks at preflight, check `.aiderignore`, `gh auth status`, Ollama, and dirty working tree state.
- If a lock blocks runs unexpectedly, inspect `var/run/agent-test.lock`; stale locks older than `STALE_LOCK_SECONDS` are removed automatically.
- Full logs remain local under `logs/`.
