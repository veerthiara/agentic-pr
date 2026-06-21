from __future__ import annotations

from agentic_pr.github_ops import Issue
from agentic_pr.planner import PlannerResult
from agentic_pr.pr_followup import FollowupTask
from agentic_pr.ci_context import CIContext
from agentic_pr.repo_instructions import RepoInstructions


def build_implementation_prompt(*, issue: Issue, run_id: str, planner_result: PlannerResult | None, repo_instructions: RepoInstructions | None = None) -> str:
    plan_text = "No planner output is available. Use the issue directly."
    if planner_result and planner_result.ok and planner_result.output:
        plan_text = planner_result.output
    instructions_section = ""
    if repo_instructions:
        parts = []
        if repo_instructions.instructions_text:
            parts.append("Project Instructions:\n" + repo_instructions.instructions_text)
        if repo_instructions.safety_text:
            parts.append("Safety Rules:\n" + repo_instructions.safety_text)
        if repo_instructions.examples_text:
            parts.append("Examples:\n" + repo_instructions.examples_text)
        
        cmds = []
        if repo_instructions.commands.get("TEST_CMD"):
            cmds.append(f"TEST_CMD: {repo_instructions.commands['TEST_CMD']}")
        if repo_instructions.commands.get("LINT_CMD"):
            cmds.append(f"LINT_CMD: {repo_instructions.commands['LINT_CMD']}")
        if cmds:
            parts.append("Repo-Specific Commands:\n" + "\n".join(cmds))
            
        if parts:
            instructions_section = "\nRepo-Specific Instructions & Guidelines:\n" + "\n\n".join(parts) + "\n"

    return f"""You are a local coding agent working in this git repository.

Run ID: {run_id}
GitHub issue: #{issue.number}
Title: {issue.title}

Original issue body:
{issue.body}

Planner output / implementation plan:
{plan_text}
{instructions_section}
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
    ci_context: CIContext | None = None,
    repo_instructions: RepoInstructions | None = None,
) -> str:
    plan_text = "No planner output is available. Use the command directly."
    if planner_result and planner_result.ok and planner_result.output:
        plan_text = planner_result.output
    
    # Build CI context section if this is a CI fix
    ci_section = ""
    if task.is_ci_fix and ci_context:
        if ci_context.checks_found:
            ci_section = f"""
CI Context:
{ci_context.summary}

Failed Checks: {', '.join(ci_context.failed_check_names) if ci_context.failed_check_names else 'None'}

CI Log Excerpts:
{ci_context.log_excerpt if ci_context.log_excerpt else 'No log excerpts available.'}

CI Warnings: {'; '.join(ci_context.warnings) if ci_context.warnings else 'None'}
"""
        else:
            ci_section = """
CI Context:
No GitHub checks found for this PR. Continuing without CI context.
"""
    
    instructions_section = ""
    if repo_instructions:
        parts = []
        if repo_instructions.instructions_text:
            parts.append("Project Instructions:\n" + repo_instructions.instructions_text)
        if repo_instructions.safety_text:
            parts.append("Safety Rules:\n" + repo_instructions.safety_text)
        if repo_instructions.examples_text:
            parts.append("Examples:\n" + repo_instructions.examples_text)
        
        cmds = []
        if repo_instructions.commands.get("TEST_CMD"):
            cmds.append(f"TEST_CMD: {repo_instructions.commands['TEST_CMD']}")
        if repo_instructions.commands.get("LINT_CMD"):
            cmds.append(f"LINT_CMD: {repo_instructions.commands['LINT_CMD']}")
        if cmds:
            parts.append("Repo-Specific Commands:\n" + "\n".join(cmds))
            
        if parts:
            instructions_section = "\nRepo-Specific Instructions & Guidelines:\n" + "\n\n".join(parts) + "\n"

    return f"""You are a local coding agent working on a follow-up for an existing pull request.

Run ID: {run_id}
PR: #{task.pr_number}
PR Title: {task.pr_title}
PR Branch: {task.head_branch}
Base Branch: {task.base_branch}

Follow-up command from @{task.comment_author}:
{task.command_text}
{ci_section}

Planner output / implementation plan:
{plan_text}
{instructions_section}
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
{f'- Fix the root cause of the failing CI checks. Prefer minimal changes.' if task.is_ci_fix else ''}
{f'- Update tests only if needed to fix the actual issue. Do not remove tests just to make CI pass.' if task.is_ci_fix else ''}
{f'- Do not weaken assertions unless clearly correct.' if task.is_ci_fix else ''}
{f"- Preserve the PR's existing intent." if task.is_ci_fix else ''}
"""
