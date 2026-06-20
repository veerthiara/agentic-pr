from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    comment_issue,
    create_pr,
    get_oldest_todo_issue,
    mark_done,
    mark_failed,
    mark_no_changes,
    set_running,
)
from agentic_pr.run_record import RunRecord, write_run_record
from agentic_pr.status import (
    before_aider_comment,
    failed_comment,
    generate_run_id,
    no_changes_comment,
    pr_body,
    pr_created_comment,
    short_error,
    start_comment,
)

RunStatus = Literal["no_issue", "no_changes", "pr_created", "failed"]


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    issue_number: int | None = None
    pr_url: str | None = None
    run_id: str | None = None


def run_once(config: AgentConfig) -> RunResult:
    issue = None
    run_id = None
    branch = ""
    started_at = _now_iso()
    finished_at = None
    log_file = None
    pr_url = None
    stage = "preflight"

    try:
        ensure_clean_worktree(config.repo_path)
        checkout_base_and_reset(config.repo_path, config.base_branch)
        ensure_clean_worktree(config.repo_path)

        stage = "fetch_issue"
        issue = get_oldest_todo_issue(config)
        if issue is None:
            return RunResult("no_issue", f"No open issues found with label: {config.label_todo}")

        run_id = generate_run_id(issue.number)
        branch = branch_name(issue.number)

        stage = "mark_running"
        set_running(config, issue.number)
        if config.comment_on_start:
            comment_issue(config, issue.number, start_comment(config, run_id))

        stage = "create_branch"
        create_branch(config.repo_path, branch)

        if config.comment_on_start:
            comment_issue(config, issue.number, before_aider_comment(config, run_id))

        stage = "run_aider"
        aider_result = run_aider(config, issue, run_id)
        log_file = str(aider_result.log_file)

        stage = "check_changes"
        if not has_changes(config.repo_path):
            mark_no_changes(config, issue.number)
            if config.comment_on_no_changes:
                comment_issue(config, issue.number, no_changes_comment(run_id))
            finished_at = _now_iso()
            _write_record(
                config,
                issue=issue,
                run_id=run_id,
                branch=branch,
                status="no_changes",
                pr_url=None,
                started_at=started_at,
                finished_at=finished_at,
                log_file=log_file,
                error_summary=None,
            )
            return RunResult("no_changes", "Aider produced no changes.", issue_number=issue.number, run_id=run_id)

        stage = "commit"
        commit_all(config.repo_path, f"REV05: work on issue #{issue.number}")

        stage = "push"
        push_branch(config.repo_path, branch)

        stage = "create_pr"
        body = pr_body(
            config=config,
            issue=issue,
            run_id=run_id,
            branch=branch,
            log_file=log_file or "",
            aider_exit_code=aider_result.exit_code,
        )
        pr_url = create_pr(config, branch, f"Agent: {issue.title}", body)
        if config.comment_on_success:
            comment_issue(config, issue.number, pr_created_comment(run_id, pr_url, branch))
        mark_done(config, issue.number)

        finished_at = _now_iso()
        _write_record(
            config,
            issue=issue,
            run_id=run_id,
            branch=branch,
            status="pr_created",
            pr_url=pr_url,
            started_at=started_at,
            finished_at=finished_at,
            log_file=log_file,
            error_summary=None,
        )
        return RunResult("pr_created", f"Created PR: {pr_url}", issue_number=issue.number, pr_url=pr_url, run_id=run_id)
    except Exception as exc:
        error_summary = short_error(exc)
        finished_at = _now_iso()
        if issue is not None and run_id is not None:
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, failed_comment(run_id, stage, error_summary))
            _write_record(
                config,
                issue=issue,
                run_id=run_id,
                branch=branch,
                status="failed",
                pr_url=pr_url,
                started_at=started_at,
                finished_at=finished_at,
                log_file=log_file,
                error_summary=error_summary,
            )
            return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)
        return RunResult("failed", error_summary)


def _write_record(
    config: AgentConfig,
    *,
    issue,
    run_id: str,
    branch: str,
    status: str,
    pr_url: str | None,
    started_at: str,
    finished_at: str | None,
    log_file: str | None,
    error_summary: str | None,
) -> None:
    write_run_record(
        config.run_record_dir,
        RunRecord(
            run_id=run_id,
            issue_number=issue.number,
            issue_title=issue.title,
            owner_repo=config.owner_repo,
            model=config.model,
            base_branch=config.base_branch,
            agent_branch=branch,
            status=status,
            pr_url=pr_url,
            started_at=started_at,
            finished_at=finished_at,
            log_file=log_file,
            error_summary=error_summary,
        ),
    )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
