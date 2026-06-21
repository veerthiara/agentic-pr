# Rev 09: CI/check awareness for PR follow-up repairs

## Problem to solve
The agent can respond to PR comments like `/agent fix the failing tests`, but it does not yet gather GitHub check/CI status or failed log context. I want to comment `/agent fix-ci` on an open PR, and the Mac Studio should gather failing GitHub checks/log snippets, add that CI context to the Aider prompt, and push a follow-up commit to the same PR branch.

## Goal
Add CI-aware PR follow-up support.

## Primary command
`/agent fix-ci`

## Also support aliases
- `/agent fix checks`
- `/agent fix failing tests`

Do not make CI repair fully automatic yet. It should be manually triggered by PR comment commands in Rev 09.

## Config values added

### config/agent-test.env and config/agent-test.env.example
```env
ENABLE_CI_CONTEXT=true
CI_COMMAND_ALIASES=/agent fix-ci,/agent fix checks,/agent fix failing tests
CI_LOG_MAX_LINES=250
CI_LOG_MAX_BYTES=40000
CI_INCLUDE_SUCCESSFUL_CHECKS=false
CI_REQUIRE_FAILED_CHECKS=false
```

## Modules added

### 1. src/agentic_pr/ci.py
Responsibilities:
- Use GitHub CLI `gh` to inspect PR check status
- Prefer stable `gh` commands and parse JSON where possible
- Provide functions:
  - `get_pr_checks(config, pr_number) -> list[CheckResult]`
  - `get_failing_checks(config, pr_number) -> list[CheckResult]`
  - `has_failing_checks(config, pr_number) -> bool`
  - `get_workflow_run_logs(config, run_id, max_lines, max_bytes) -> str`
  - `get_check_run_logs(config, check_run_id, max_lines, max_bytes) -> str`
  - `_truncate_logs(logs, max_lines, max_bytes) -> str`

CheckResult includes:
- name
- state/status/conclusion if available
- details_url/link if available
- workflow/run id if available
- raw fields for debugging if needed

If `gh pr checks` is unavailable or returns non-zero because there are no checks, return an empty result with a clear reason rather than crashing.

### 2. src/agentic_pr/ci_context.py
Responsibilities:
- Build concise CI context for Aider
- For failing GitHub Actions runs, try to collect useful log snippets using `gh run view` / `gh run view --log-failed` if a run id or URL can be inferred
- Do not paste massive logs
- Respect: CI_LOG_MAX_LINES, CI_LOG_MAX_BYTES
- Include: PR number, failed check names, status/conclusion, log excerpts if available, fallback message if logs cannot be fetched
- Provide: `build_ci_context(config, pr_number) -> CIContext`

CIContext includes:
- checks_found: bool
- failing_checks_found: bool
- summary: str
- failed_check_names: list[str]
- log_excerpt: str
- warnings: list[str]

### 3. Updated src/agentic_pr/pr_followup.py
Responsibilities:
- Detect whether a `/agent` command is CI-focused
- A command is CI-focused if the full comment starts with one of CI_COMMAND_ALIASES
- Existing generic `/agent ...` follow-up should still work
- Add field to FollowupTask:
  - is_ci_fix: bool
  - ci_command_alias: str | None
- Keep processing one comment at a time
- Do not reprocess comments already in comment-state

### 4. Updated src/agentic_pr/prompt_builder.py
Add CI-aware follow-up prompt support.

When FollowupTask.is_ci_fix is true and ENABLE_CI_CONTEXT=true:
- include CIContext summary
- include failed check names
- include failed log excerpts
- instruct Aider:
  - fix the root cause of the failing checks
  - prefer minimal changes
  - update tests only if needed
  - do not remove tests just to make CI pass
  - do not weaken assertions unless clearly correct
  - preserve the PR's existing intent
  - do not create a new PR

If no checks/logs are found:
- include a clear note
- still allow Aider to inspect the repo and make a reasonable fix if the user command has enough context

### 5. Updated src/agentic_pr/orchestrator.py
In the PR follow-up flow:
- If FollowupTask.is_ci_fix and ENABLE_CI_CONTEXT=true:
  - collect CI context before running planner/Aider
  - comment on PR with a short message: "Collecting CI context for run "
  - add CI context to run record
  - add CI context to final Aider prompt
- If CI_REQUIRE_FAILED_CHECKS=true and no failing checks are found:
  - do not run Aider
  - comment that no failing checks were found
  - mark comment processed
  - update run record with status `no_failed_checks`
- If CI_REQUIRE_FAILED_CHECKS=false and no failing checks are found:
  - continue with a warning in the prompt and PR comment

### 5. Updated src/agentic_pr/run_record.py
Add fields for PR follow-up CI runs:
- is_ci_fix
- ci_checks_found
- ci_failing_checks_found
- ci_failed_check_names
- ci_context_summary
- ci_log_excerpt
- ci_log_excerpt_file if log excerpt is saved separately
- ci_warnings

If log excerpts are large, save them under var/run with the run ID:
var/run/<run_id>-ci-context.md

### 6. Updated src/agentic_pr/status.py
Add concise comment templates:
- CI context collection started
- CI context summary found failing checks
- no failing checks found
- CI fix pushed
- CI fix failed
- CI logs unavailable but continuing

Keep comments short. Do not paste huge logs into GitHub comments.

### 7. Updated src/agentic_pr/github_ops.py
Add helpers if needed:
- get PR checks
- get workflow run logs
- comment on PR
- optionally extract run id from check URL if possible

Use `gh` CLI through command.py, not raw token handling.

### 8. Updated src/agentic_pr/cli.py
Keep existing:
- doctor
- ensure-labels
- run-once
- run-followup-once
- poll

Added:
- python -m agentic_pr.cli ci-summary --config config/agent-test.env --pr

### 9. Updated Makefile
Added target:
- make ci-summary CONFIG=config/agent-test.env PR=15

If implemented, it should print check summary and failed log snippets without running Aider.

## Tests added

### tests/test_ci.py
- `/agent fix-ci` is detected as CI fix
- `/agent fix checks` is detected as CI fix
- generic `/agent update README` is not CI fix
- no checks found does not crash
- failed check summary is included
- long CI logs are truncated by lines
- long CI logs are truncated by bytes
- CI prompt includes failed check names and log excerpt
- CI prompt says not to delete/weaken tests just to pass CI
- run record supports CI fields
- ci-summary command can be tested with mocked command outputs if practical

### tests/test_ci_context.py
- truncating long logs by lines
- truncating long logs by bytes
- no checks found
- failed checks without logs
- failed checks with logs

### Updated existing tests
- tests/test_pr_followup.py - CI command detection tests
- tests/test_prompt_builder.py - CI context in prompt tests
- tests/test_run_record.py - CI fields tests
- tests/test_status.py - CI comment template tests
- tests/test_config.py - CI config fields tests
- tests/test_comment_state.py, test_aider_runner.py, test_planner.py, test_poller.py, test_preflight.py, test_safety.py - updated _config() helpers

Unit tests must not call real GitHub, Aider, Ollama, launchd, or network.

## Documentation

### Updated
- README.md - Added "CI-Aware PR Follow-up (Rev 09)" section
- plan/rev-09.md - This file

Rev 09 docs explain:
- what CI-aware follow-up does
- supported commands
- how CI context is collected
- where CI context/log snippets are saved
- config values
- how to test manually
- limitations: only manually triggered in Rev 09, if no GitHub Actions/checks exist it may continue with a warning, it does not auto-merge, it does not automatically retry failed CI yet

## Acceptance test

### Prerequisites
- There is an open PR
- Ideally the PR has a failing GitHub Actions check
- Service is running or manual command can be used

### Manual test
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

### Fallback test when no CI exists
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

## Files changed
- config/agent-test.env
- config/agent-test.env.example
- src/agentic_pr/config.py
- src/agentic_pr/ci.py (new)
- src/agentic_pr/ci_context.py (new)
- src/agentic_pr/pr_followup.py
- src/agentic_pr/prompt_builder.py
- src/agentic_pr/orchestrator.py
- src/agentic_pr/run_record.py
- src/agentic_pr/status.py
- src/agentic_pr/github_ops.py
- src/agentic_pr/cli.py
- Makefile
- tests/test_ci.py (new)
- tests/test_ci_context.py (new)
- tests/test_config.py
- tests/test_pr_followup.py
- tests/test_prompt_builder.py
- tests/test_run_record.py
- tests/test_status.py
- tests/test_comment_state.py
- tests/test_aider_runner.py
- tests/test_planner.py
- tests/test_poller.py
- tests/test_preflight.py
- tests/test_safety.py
- README.md
- plan/rev-09.md (new)

## Validation
- make test: 73 tests pass
- make doctor CONFIG=config/agent-test.env: All checks pass
- make ensure-labels CONFIG=config/agent-test.env: Labels created