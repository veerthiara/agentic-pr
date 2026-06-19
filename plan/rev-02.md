Rev 02 brief plan

Rev 02 should be:

Convert the shell runner into a small Python CLI project.
Keep Makefile commands.
Keep gh CLI for GitHub operations.
Keep Aider as external command.
Do not add polling yet.

The new structure should look like this:

agentic-pr/
├── README.md
├── Makefile
├── pyproject.toml
├── config/
│   ├── agent-test.env.example
│   └── agent-test.env
├── src/
│   └── agentic_pr/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── command.py
│       ├── doctor.py
│       ├── github_ops.py
│       ├── git_ops.py
│       ├── aider_runner.py
│       └── orchestrator.py
├── tests/
│   ├── test_config.py
│   └── test_command.py
├── logs/
└── var/
    └── run/

The commands should become:

make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make run-once CONFIG=config/agent-test.env

Internally they call Python:

python -m agentic_pr.cli doctor --config config/agent-test.env
python -m agentic_pr.cli ensure-labels --config config/agent-test.env
python -m agentic_pr.cli run-once --config config/agent-test.env
Rev 02 detailed changes
1. Add pyproject.toml

Use only standard Python dependencies for now. No Typer, no Click, no PyGithub yet.

[project]
name = "agentic-pr"
version = "0.1.0"
description = "Local Mac Studio GitHub issue to PR coding agent"
requires-python = ">=3.11"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

Why: keep it simple. Use argparse, subprocess, dataclasses, and pathlib.

2. Keep Makefile, but make it call Python

Example Makefile direction:

CONFIG ?= config/agent-test.env
PYTHON ?= python3

doctor:
	$(PYTHON) -m agentic_pr.cli doctor --config $(CONFIG)

ensure-labels:
	$(PYTHON) -m agentic_pr.cli ensure-labels --config $(CONFIG)

run-once:
	$(PYTHON) -m agentic_pr.cli run-once --config $(CONFIG)

test:
	$(PYTHON) -m pytest
3. config.py

Responsibilities:

Load .env config file
Validate required fields
Expose typed AgentConfig object

Required fields:

REPO_PATH
OWNER_REPO
BASE_BRANCH
MODEL
LABEL_TODO
LABEL_RUNNING
LABEL_DONE
LABEL_FAILED
OLLAMA_API_BASE

Optional fields for Rev 02:

AIDER_EXTRA_ARGS
LOG_DIR
RUN_DIR
4. command.py

This is important. All shell commands should go through one helper.

Responsibilities:

Run commands safely
Capture stdout/stderr
Support cwd/env
Raise useful errors
Mask secrets if needed later

Example conceptual API:

run(["gh", "auth", "status"])
run(["git", "status", "--short"], cwd=config.repo_path)

This makes the project much cleaner than shell.

5. doctor.py

Checks:

gh installed
gh auth status works
git installed
jq installed — optional if Python replaces jq
aider installed
ollama API responds
repo path exists
repo path is git repo
OWNER_REPO accessible
working tree clean

Since Python can parse JSON, jq is no longer strictly needed. But you can keep checking it for Rev 02 if your existing shell still uses it.

6. github_ops.py

Use gh CLI from Python.

Functions:

get_oldest_todo_issue(config)
ensure_labels(config)
add_label(issue_number, label)
remove_label(issue_number, label)
comment_issue(issue_number, body)
create_pr(base, head, title, body)

Use:

gh issue list --repo OWNER_REPO --label agent-run --state open --limit 1 --json number,title,body,createdAt
gh issue edit ISSUE --add-label agent-running --remove-label agent-run
gh issue comment ISSUE --body "..."
gh pr create ...

Do not use GitHub REST API yet. Since gh auth already works, the CLI avoids token handling.

7. git_ops.py

Functions:

ensure_clean_worktree(repo_path)
checkout_base_and_reset(repo_path, base_branch)
create_branch(repo_path, branch_name)
has_changes(repo_path)
commit_all(repo_path, message)
push_branch(repo_path, branch_name)

Use normal git commands underneath.

8. aider_runner.py

Responsibilities:

Build prompt file
Run aider non-interactively
Write full logs
Return exit code

Command should still be:

aider \
  --model "$MODEL" \
  --no-auto-commits \
  --yes-always \
  --message-file "$PROMPT_FILE"

Optional later:

--test-cmd
--lint-cmd
--auto-test
--auto-lint

Do not add those until basic flow is stable.

9. orchestrator.py

This is the main workflow.

Flow:

load config
doctor-light checks
fetch oldest agent-run issue
mark issue agent-running
checkout/reset main
create branch
build prompt
run aider
if no changes:
    comment no changes
    remove agent-running
    stop
commit changes
push branch
create PR
comment issue with PR URL
remove agent-running
add agent-pr-created
on failure:
    add agent-failed
    remove agent-running
    comment short failure
10. Tests

Rev 02 tests should not run Aider or GitHub for real.

Add unit tests for:

config file parsing
missing required config fails
command helper captures output
branch name generation
prompt generation

Integration testing still remains manual:

make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make run-once CONFIG=config/agent-test.env
