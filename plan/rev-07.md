Rev 07 — Planner and repo context stage

Goal: improve broader Copilot-like tasks by planning before implementation.

Flow:

```text
GitHub issue -> repo context summary -> planner -> GitHub planning comment -> Aider implementation prompt -> safety checks -> validation -> PR
```

Config values:

```env
ENABLE_PLANNER=true
PLANNER_MODEL=ollama/qwen3-coder:30b
REPO_CONTEXT_MAX_FILES=80
REPO_CONTEXT_MAX_BYTES=120000
PLANNER_TIMEOUT_SECONDS=900
COMMENT_PLAN=true
```

Files added:

- `src/agentic_pr/repo_context.py`
- `src/agentic_pr/planner.py`
- `src/agentic_pr/prompt_builder.py`
- `tests/test_repo_context.py`
- `tests/test_planner.py`
- `tests/test_prompt_builder.py`

Behavior:

- Collects a lightweight repo snapshot while ignoring secrets, `.env`, dependency folders, generated folders, and caches.
- Runs a local Ollama planner with `PLANNER_MODEL`.
- Saves planner output to `var/run/<run_id>-planner.md`.
- Comments a concise planning result on the GitHub issue when `COMMENT_PLAN=true`.
- Builds a stronger Aider prompt that includes the issue, run ID, planner output, and explicit permission to create files when needed.
- Falls back to the raw issue prompt if the planner fails or times out.
- Adds planner fields to JSON run records.

Acceptance test:

```sh
make test
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make status-service
```

GitHub issue:

Title: `Agent test: convert calculator into FastAPI app`

Body:

```text
Convert this repository into a small FastAPI application.

Requirements:

1. Add a FastAPI app with two routes:
   GET /health returns {"status": "ok"}
2. GET /add?a=1&b=2 returns {"result": 3}
3. Keep existing calculator functions if useful.
4. Add or update tests.
5. Add minimal dependency/config files if needed.
6. Update README with how to run the app.
7. Keep the implementation simple.
```

Label: `agent-run`

Expected:

- issue gets `agent-running`
- issue gets a planning comment
- planner output is saved locally
- Aider runs with the planner-enhanced implementation prompt
- PR is created
- PR includes plan summary
- run record includes planner fields
