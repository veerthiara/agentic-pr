from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentic_pr.aider_runner import run_aider
from agentic_pr.config import AgentConfig
from agentic_pr.git_ops import (
    branch_name,
    checkout_base_and_reset,
    commit_all,
    create_branch,
    ensure_clean_worktree,
    has_changes,
    push_branch,
)
from agentic_pr.github_ops import (
    clear_running,
    comment_issue,
    create_pr,
    get_oldest_todo_issue,
    mark_done,
    mark_failed,
    set_running,
)

RunStatus = Literal["no_issue", "no_changes", "pr_created", "failed"]


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    issue_number: int | None = None
    pr_url: str | None = None


def run_once(config: AgentConfig) -> RunResult:
    issue = None

    try:
        ensure_clean_worktree(config.repo_path)
        checkout_base_and_reset(config.repo_path, config.base_branch)
        ensure_clean_worktree(config.repo_path)

        issue = get_oldest_todo_issue(config)
        if issue is None:
            return RunResult("no_issue", f"No open issues found with label: {config.label_todo}")

        set_running(config, issue.number)
        branch = branch_name(issue.number)
        create_branch(config.repo_path, branch)
        aider_result = run_aider(config, issue)

        if not has_changes(config.repo_path):
            comment_issue(
                config,
                issue.number,
                "Local agent ran, but produced no file changes.\n\n"
                f"Log path: {aider_result.log_file}\n"
                f"Aider exit code: {aider_result.exit_code}",
            )
            clear_running(config, issue.number)
            return RunResult("no_changes", "Aider produced no changes.", issue_number=issue.number)

        commit_all(config.repo_path, f"REV03: work on issue #{issue.number}")
        push_branch(config.repo_path, branch)

        pr_body = (
            "This PR was created by the local agent.\n\n"
            f"Closes #{issue.number}\n\n"
            f"Model: {config.model}\n\n"
            "Notes:\n"
            "- Review carefully before merging.\n"
            f"- Local log path: {aider_result.log_file}\n"
            f"- Aider exit code: {aider_result.exit_code}\n"
        )
        pr_url = create_pr(config, branch, f"Agent: {issue.title}", pr_body)
        comment_issue(config, issue.number, f"Created PR: {pr_url}")
        mark_done(config, issue.number)
        return RunResult("pr_created", f"Created PR: {pr_url}", issue_number=issue.number, pr_url=pr_url)
    except Exception as exc:
        if issue is not None:
            mark_failed(config, issue.number)
            comment_issue(config, issue.number, f"Local agent failed while working on this issue:\n\n{exc}")
            return RunResult("failed", str(exc), issue_number=issue.number)
        return RunResult("failed", str(exc))
