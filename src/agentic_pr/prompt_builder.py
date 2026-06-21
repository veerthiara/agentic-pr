from __future__ import annotations

from agentic_pr.github_ops import Issue
from agentic_pr.planner import PlannerResult
from agentic_pr.pr_followup import FollowupTask


def build_implementation_prompt(*, issue: Issue, run_id: str, planner_result: PlannerResult | None) -> str:
    plan_text = "No planner output is available. Use the issue directly."
    if planner_result and planner_result.ok and planner_result.output:
        plan_text = planner_result.output
    return f"""You are a local coding agent working in this git repository.

Run ID: {run_id}
GitHub issue: #{issue.number}
Title: {issue.title}

Original issue body:
{issue.body}

Planner output / implementation plan:
{plan_text}

Implementation instructions:
- Implement the issue completely, using the planner output when helpful.
- Creating new files is allowed when needed.
- Updating existing files is allowed when needed.
- Deleting files is allowed only when clearly necessary and safe.
- Add or update tests when appropriate.
- Keep changes minimal but complete.
- Update README/docs when the task changes app behavior or usage.
- Do not edit secrets, credentials, .env files, private keys, dependency folders, generated folders, or build outputs.
- Do not merge anything. Only make code changes for a PR.
"""


def build_followup_prompt(
    *,
    task: FollowupTask,
    run_id: str,
    planner_result: PlannerResult | None,
) -> str:
    plan_text = "No planner output is available. Use the command directly."
    if planner_result and planner_result.ok and planner_result.output:
        plan_text = planner_result.output
    return f"""You are a local coding agent working on a follow-up for an existing pull request.

Run ID: {run_id}
PR: #{task.pr_number}
PR Title: {task.pr_title}
PR Branch: {task.head_branch}
Base Branch: {task.base_branch}

Follow-up command from @{task.comment_author}:
{task.command_text}

Planner output / implementation plan:
{plan_text}

Implementation instructions:
- This is a follow-up on an existing PR. Do NOT create a new branch or PR.
- Preserve the existing PR intent and changes.
- Make the smallest additional change needed to address the follow-up command.
- Avoid unrelated refactors.
- Creating new files is allowed when needed.
- Updating existing files is allowed when needed.
- Deleting files is allowed only when clearly necessary and safe.
- Add or update tests when appropriate.
- Keep changes minimal but complete.
- Update README/docs when the task changes app behavior or usage.
- Do not edit secrets, credentials, .env files, private keys, dependency folders, generated folders, or build outputs.
- Do not merge anything. Only make code changes for the existing PR.
"""
