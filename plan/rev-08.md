Rev 08 — Iterative PR repair from PR comments

Goal: continue the same agent session from GitHub PR comments.

Flow:

```text
Existing open PR comment starting with `/agent` -> local Mac Studio follow-up run -> Aider edits same PR branch -> safety checks -> optional tests/lint -> commit and push to same PR
```

Config values:

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

Files added:

- `src/agentic_pr/comment_state.py`
- `src/agentic_pr/pr_followup.py`
- `tests/test_comment_state.py`
- `tests/test_pr_followup.py`

Files updated:

- `src/agentic_pr/config.py` (new config fields)
- `src/agentic_pr/github_ops.py` (PR helpers)
- `src/agentic_pr/git_ops.py` (checkout existing branch)
- `src/agentic_pr/prompt_builder.py` (follow-up prompt)
- `src/agentic_pr/run_record.py` (follow-up fields)
- `src/agentic_pr/status.py` (follow-up comment templates)
- `src/agentic_pr/orchestrator.py` (run_pr_followup_once)
- `src/agentic_pr/poller.py` (process follow-ups)
- `src/agentic_pr/cli.py` (run-followup-once command)
- `src/agentic_pr/planner.py` (accept FollowupTask)
- `Makefile` (run-followup-once target)
- `config/agent-test.env` and `config/agent-test.env.example`
- `README.md`
- `tests/test_prompt_builder.py`
- `tests/test_run_record.py`
- `tests/test_status.py`
- `tests/test_poller.py`

Behavior:

- Tracks processed PR comment IDs locally so the same `/agent` comment is not processed twice.
- Stores state under `COMMENT_STATE_DIR` with one JSON file per repo/PR.
- Finds one pending follow-up command from open PRs per cycle.
- A follow-up command is a PR comment whose body starts with `PR_FOLLOWUP_COMMAND_PREFIX` (default `/agent`).
- Ignores comments already processed in comment_state.
- Ignores comments from bots.
- Processes only one follow-up comment per cycle.
- If `PR_FOLLOWUP_REQUIRE_LABEL=true`, only processes PRs with `LABEL_FOLLOWUP`.
- Returns a structured `FollowupTask` with PR details, comment info, and command text.
- Uses `gh CLI` with Python JSON parsing.
- Checkouts the existing PR head branch (fetch origin, checkout, reset to origin/branch).
- Runs optional Rev 07 planner/repo context if `ENABLE_PLANNER=true`.
- Builds follow-up Aider prompt with PR context, command, and explicit "do not create new PR" instruction.
- Runs Aider with timeout.
- If no changes: comments no changes, marks comment processed, updates run record, removes running label.
- If changes exist: runs Rev 06 safety checks, runs optional LINT_CMD and TEST_CMD.
- If safety/test/lint fails: does not push, comments failed/blocked, updates run record, removes running label, marks comment processed.
- If checks pass: commits with message `agent: follow up on PR #N`, pushes to same PR branch, gets commit SHA, comments success with commit SHA, adds `LABEL_FOLLOWUP_DONE`, removes `LABEL_FOLLOWUP_RUNNING`, marks comment processed, updates run record.
- Always releases lock in finally.
- Poller processes one issue task then one PR follow-up task per cycle (if enabled).
- New CLI command: `python -m agentic_pr.cli run-followup-once --config config/agent-test.env`
- New Makefile target: `make run-followup-once CONFIG=config/agent-test.env`
- Labels created by `ensure-labels`: agent-followup, agent-followup-running, agent-followup-done, agent-followup-failed.
- Run records include `run_type="pr_followup"`, `pr_number`, `pr_title`, `comment_id`, `command_text`, `commit_sha`.

Acceptance test:

```sh
make test
make doctor CONFIG=config/agent-test.env
make ensure-labels CONFIG=config/agent-test.env
make status-service
```

Prerequisites:
- There is an open PR created by the agent.
- Service is running or poller is running.

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