from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from agentic_pr.aider_runner import run_aider
from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.git_ops import branch_name, checkout_base_and_reset, commit_all, create_branch, has_changes, push_branch
from agentic_pr.github_ops import comment_issue, create_pr, get_oldest_todo_issue, mark_blocked, mark_done, mark_failed, mark_no_changes, set_running
from agentic_pr.lock import FileLock, LockAlreadyHeld
from agentic_pr.planner import PlannerResult, run_planner
from agentic_pr.preflight import run_preflight
from agentic_pr.prompt_builder import build_implementation_prompt
from agentic_pr.repo_context import build_repo_context
from agentic_pr.run_record import RunRecord, write_run_record
from agentic_pr.safety import check_safety
from agentic_pr.status import (
    aider_timeout_comment,
    blocked_comment,
    failed_comment,
    generate_run_id,
    implementation_started_comment,
    no_changes_comment,
    planner_completed_comment,
    planner_failed_comment,
    planner_started_comment,
    pr_body,
    pr_created_comment,
    preflight_blocked_comment,
    short_error,
    start_comment,
    validation_failed_comment,
)

RunStatus = Literal["no_issue", "no_changes", "pr_created", "failed", "blocked"]


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    message: str
    issue_number: int | None = None
    pr_url: str | None = None
    run_id: str | None = None


def run_once(config: AgentConfig) -> RunResult:
    lock = FileLock(config.lock_file, stale_seconds=config.stale_lock_seconds)
    try:
        lock.acquire()
    except LockAlreadyHeld as exc:
        return RunResult("blocked", str(exc))

    issue = None
    run_id = None
    branch = ""
    started_at = _now_iso()
    log_file = None
    pr_url = None
    stage = "fetch_issue"
    planner_result: PlannerResult | None = None

    try:
        issue = get_oldest_todo_issue(config)
        if issue is None:
            return RunResult("no_issue", f"No open issues found with label: {config.label_todo}")

        run_id = generate_run_id(issue.number)
        branch = branch_name(issue.number)

        stage = "mark_running"
        set_running(config, issue.number)
        if config.comment_on_start:
            comment_issue(config, issue.number, start_comment(config, run_id))

        stage = "preflight"
        preflight = run_preflight(config)
        if not preflight.ok:
            return _blocked(config, issue=issue, run_id=run_id, branch=branch, started_at=started_at, log_file=log_file, reason=preflight.reason or "preflight_failed", details=preflight.details, comment=preflight_blocked_comment(run_id, preflight.reason or "preflight_failed", preflight.details), planner_result=planner_result)

        stage = "checkout_base"
        checkout_base_and_reset(config.repo_path, config.base_branch)

        stage = "create_branch"
        create_branch(config.repo_path, branch)

        stage = "planner"
        planner_result = _maybe_plan(config, issue, run_id)
        if config.comment_plan and config.enable_planner:
            if planner_result and planner_result.ok:
                comment_issue(config, issue.number, planner_completed_comment(run_id, planner_result.summary))
            elif planner_result:
                comment_issue(config, issue.number, planner_failed_comment(run_id, planner_result.error))

        implementation_prompt = build_implementation_prompt(issue=issue, run_id=run_id, planner_result=planner_result)
        if config.comment_plan:
            comment_issue(config, issue.number, implementation_started_comment(run_id))

        stage = "run_aider"
        aider_result = run_aider(config, issue, run_id, prompt=implementation_prompt)
        log_file = str(aider_result.log_file)
        if aider_result.timed_out:
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, aider_timeout_comment(run_id, config.aider_timeout_seconds))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=f"Aider timed out after {config.aider_timeout_seconds} seconds", planner_result=planner_result)
            return RunResult("failed", f"Aider timed out after {config.aider_timeout_seconds} seconds", issue_number=issue.number, run_id=run_id)

        stage = "check_changes"
        if not has_changes(config.repo_path):
            mark_no_changes(config, issue.number)
            if config.comment_on_no_changes:
                comment_issue(config, issue.number, no_changes_comment(run_id))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="no_changes", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result)
            return RunResult("no_changes", "Aider produced no changes.", issue_number=issue.number, run_id=run_id)

        stage = "safety"
        safety = check_safety(config)
        if not safety.ok:
            return _blocked(config, issue=issue, run_id=run_id, branch=branch, started_at=started_at, log_file=log_file, reason=safety.reason or "safety_failed", details=safety.details, comment=blocked_comment(run_id, safety.reason or "safety_failed", safety.details), planner_result=planner_result)

        stage = "lint"
        validation = _run_validation(config, config.lint_cmd, "lint")
        if validation is not None:
            return _failed_validation(config, issue, run_id, branch, started_at, log_file, "lint", validation, planner_result)

        stage = "test"
        validation = _run_validation(config, config.test_cmd, "test")
        if validation is not None:
            return _failed_validation(config, issue, run_id, branch, started_at, log_file, "test", validation, planner_result)

        stage = "commit"
        commit_all(config.repo_path, f"REV07: work on issue #{issue.number}")

        stage = "push"
        push_branch(config.repo_path, branch)

        stage = "create_pr"
        body = pr_body(config=config, issue=issue, run_id=run_id, branch=branch, log_file=log_file or "", aider_exit_code=aider_result.exit_code, planner_enabled=config.enable_planner, plan_summary=planner_result.summary if planner_result else None)
        pr_url = create_pr(config, branch, f"Agent: {issue.title}", body)
        if config.comment_on_success:
            comment_issue(config, issue.number, pr_created_comment(run_id, pr_url, branch))
        mark_done(config, issue.number)
        _write_record(config, issue=issue, run_id=run_id, branch=branch, status="pr_created", pr_url=pr_url, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result)
        return RunResult("pr_created", f"Created PR: {pr_url}", issue_number=issue.number, pr_url=pr_url, run_id=run_id)
    except Exception as exc:
        error_summary = short_error(exc)
        if issue is not None and run_id is not None:
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, failed_comment(run_id, stage, error_summary))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=pr_url, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result)
            return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)
        return RunResult("failed", error_summary)
    finally:
        lock.release()


def _maybe_plan(config: AgentConfig, issue, run_id: str) -> PlannerResult | None:
    if not config.enable_planner:
        return None
    if config.comment_plan:
        comment_issue(config, issue.number, planner_started_comment(run_id))
    context = build_repo_context(config.repo_path, max_files=config.repo_context_max_files, max_bytes=config.repo_context_max_bytes)
    return run_planner(config, issue, context, run_id)


def _run_validation(config: AgentConfig, command: str, name: str) -> str | None:
    if not command.strip():
        return None
    result = run(shlex.split(command), cwd=config.repo_path, check=False)
    if result.returncode == 0:
        return None
    return short_error(RuntimeError(f"{name} failed with exit code {result.returncode}: {result.stderr or result.stdout}"))


def _blocked(config: AgentConfig, *, issue, run_id: str, branch: str, started_at: str, log_file: str | None, reason: str, details: list[str], comment: str, planner_result: PlannerResult | None) -> RunResult:
    mark_blocked(config, issue.number)
    comment_issue(config, issue.number, comment)
    error_summary = f"{reason}: {'; '.join(details[:3])}"
    _write_record(config, issue=issue, run_id=run_id, branch=branch, status="blocked", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result)
    return RunResult("blocked", error_summary, issue_number=issue.number, run_id=run_id)


def _failed_validation(config: AgentConfig, issue, run_id: str, branch: str, started_at: str, log_file: str | None, command_name: str, error_summary: str, planner_result: PlannerResult | None) -> RunResult:
    mark_failed(config, issue.number)
    if config.comment_on_failure:
        comment_issue(config, issue.number, validation_failed_comment(run_id, command_name, error_summary))
    _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result)
    return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)


def _write_record(config: AgentConfig, *, issue, run_id: str, branch: str, status: str, pr_url: str | None, started_at: str, finished_at: str | None, log_file: str | None, error_summary: str | None, planner_result: PlannerResult | None) -> None:
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
            planner_enabled=config.enable_planner,
            planner_status=planner_result.status if planner_result else ("disabled" if not config.enable_planner else None),
            planner_output_file=str(planner_result.output_file) if planner_result and planner_result.output_file else None,
            plan_summary=planner_result.summary if planner_result else None,
            planned_files_to_modify=planner_result.files_to_modify if planner_result else [],
            planned_files_to_create=planner_result.files_to_create if planner_result else [],
            planned_test_plan=planner_result.test_plan if planner_result else None,
        ),
    )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
