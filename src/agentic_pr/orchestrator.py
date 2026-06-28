from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.ci_context import CIContext, build_ci_context
from agentic_pr.engine import get_engine
from agentic_pr.engines.base import EngineRequest
from agentic_pr.git_ops import branch_name, checkout_base_and_reset, checkout_existing_branch, commit_all, create_branch, current_commit, has_changes, push_branch
from agentic_pr.github_ops import add_label_to_pr_or_issue, comment_issue, comment_pr, create_pr, get_oldest_todo_issue, mark_blocked, mark_done, mark_failed, mark_no_changes, remove_label_from_pr_or_issue, set_running
from agentic_pr.lock import FileLock, LockAlreadyHeld
from agentic_pr.planner import PlannerResult, run_planner
from agentic_pr.preflight import run_preflight
from agentic_pr.prompt_builder import build_followup_prompt, build_implementation_prompt
from agentic_pr.pr_followup import FollowupTask, accept_followup_comment, find_pending_followup, mark_comment_processed
from agentic_pr.repo_context import build_repo_context
from agentic_pr.run_record import RunRecord, write_run_record
from agentic_pr.safety import check_safety
from agentic_pr.status import (
    blocked_comment,
    before_engine_comment,
    failed_comment,
    followup_accepted_comment,
    followup_blocked_comment,
    followup_failed_comment,
    followup_no_changes_comment,
    followup_pushed_comment,
    followup_started_comment,
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
    engine_timeout_comment,
    validation_failed_comment,
    ci_context_collecting_comment,
    ci_context_no_failing_checks_comment,
    ci_context_no_checks_comment,
    ci_fix_pushed_comment,
    ci_fix_failed_comment,
    ci_logs_unavailable_comment,
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

        implementation_prompt = build_implementation_prompt(issue=issue, run_id=run_id, planner_result=planner_result, repo_instructions=config.repo_instructions)
        if config.comment_plan:
            comment_issue(config, issue.number, implementation_started_comment(config, run_id))

        stage = "run_engine"
        engine = get_engine(config)
        prompt_file = config.run_dir / f"{run_id}-prompt.md"
        log_file = config.log_dir / f"{run_id}.log"
        prompt_file.write_text(implementation_prompt)
        if config.comment_on_start:
            comment_issue(config, issue.number, before_engine_comment(config, run_id))
        
        request = EngineRequest(
            run_id=run_id,
            repo_path=config.repo_path,
            prompt_file=prompt_file,
            prompt_text=implementation_prompt,
            model=config.model,
            log_file=log_file,
            timeout_seconds=config.engine_timeout_seconds,
            mode="issue",
        )
        engine_result = engine.run(request)
        log_file = str(engine_result.log_file)
        if engine_result.timed_out:
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, engine_timeout_comment(config, run_id, config.engine_timeout_seconds))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=f"Engine timed out after {config.engine_timeout_seconds} seconds", planner_result=planner_result, engine_result=engine_result)
            return RunResult("failed", f"Engine timed out after {config.engine_timeout_seconds} seconds", issue_number=issue.number, run_id=run_id)
        if not engine_result.ok:
            error_summary = engine_result.error_summary or f"Engine exited with code {engine_result.exit_code}"
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, failed_comment(run_id, "run_engine", error_summary))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, engine_result=engine_result)
            return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)

        stage = "check_changes"
        if not has_changes(config.repo_path):
            mark_no_changes(config, issue.number)
            if config.comment_on_no_changes:
                comment_issue(config, issue.number, no_changes_comment(run_id))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="no_changes", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result, engine_result=engine_result)
            return RunResult("no_changes", "Engine produced no changes.", issue_number=issue.number, run_id=run_id)

        stage = "safety"
        safety = check_safety(config)
        if not safety.ok:
            return _blocked(config, issue=issue, run_id=run_id, branch=branch, started_at=started_at, log_file=log_file, reason=safety.reason or "safety_failed", details=safety.details, comment=blocked_comment(run_id, safety.reason or "safety_failed", safety.details), planner_result=planner_result, engine_result=engine_result)

        stage = "lint"
        validation = _run_validation(config, config.lint_cmd, "lint")
        if validation is not None:
            return _failed_validation(config, issue, run_id, branch, started_at, log_file, "lint", validation, planner_result, engine_result=engine_result)

        stage = "test"
        validation = _run_validation(config, config.test_cmd, "test")
        if validation is not None:
            return _failed_validation(config, issue, run_id, branch, started_at, log_file, "test", validation, planner_result, engine_result=engine_result)

        stage = "commit"
        commit_all(config.repo_path, f"REV07: work on issue #{issue.number}")

        stage = "push"
        push_branch(config.repo_path, branch)

        stage = "create_pr"
        body = pr_body(config=config, issue=issue, run_id=run_id, branch=branch, log_file=log_file or "", engine_exit_code=engine_result.exit_code, planner_enabled=config.enable_planner, plan_summary=planner_result.summary if planner_result else None)
        pr_url = create_pr(config, branch, f"Agent: {issue.title}", body)
        if config.comment_on_success:
            comment_issue(config, issue.number, pr_created_comment(run_id, pr_url, branch))
        mark_done(config, issue.number)
        _write_record(config, issue=issue, run_id=run_id, branch=branch, status="pr_created", pr_url=pr_url, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result, engine_result=engine_result)
        return RunResult("pr_created", f"Created PR: {pr_url}", issue_number=issue.number, pr_url=pr_url, run_id=run_id)
    except Exception as exc:
        error_summary = short_error(exc)
        if issue is not None and run_id is not None:
            mark_failed(config, issue.number)
            if config.comment_on_failure:
                comment_issue(config, issue.number, failed_comment(run_id, stage, error_summary))
            _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=pr_url, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, engine_result=None)
            return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)
        return RunResult("failed", error_summary)
    finally:
        lock.release()


def _maybe_plan(config: AgentConfig, issue, run_id: str) -> PlannerResult | None:
    if not config.enable_planner:
        return None
    if config.comment_plan:
        comment_issue(config, issue.number, planner_started_comment(run_id))
    repo_instruction_files = config.repo_instructions.files_found if config.repo_instructions else None
    context = build_repo_context(config.repo_path, max_files=config.repo_context_max_files, max_bytes=config.repo_context_max_bytes, repo_instruction_files=repo_instruction_files)
    return run_planner(config, issue, context, run_id, repo_instructions=config.repo_instructions)


def _run_validation(config: AgentConfig, command: str, name: str) -> str | None:
    if not command.strip():
        return None
    result = run(shlex.split(command), cwd=config.repo_path, check=False)
    if result.returncode == 0:
        return None
    return short_error(RuntimeError(f"{name} failed with exit code {result.returncode}: {result.stderr or result.stdout}"))


def _blocked(config: AgentConfig, *, issue, run_id: str, branch: str, started_at: str, log_file: str | None, reason: str, details: list[str], comment: str, planner_result: PlannerResult | None, engine_result=None) -> RunResult:
    mark_blocked(config, issue.number)
    comment_issue(config, issue.number, comment)
    error_summary = f"{reason}: {'; '.join(details[:3])}"
    _write_record(config, issue=issue, run_id=run_id, branch=branch, status="blocked", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, engine_result=engine_result)
    return RunResult("blocked", error_summary, issue_number=issue.number, run_id=run_id)


def _failed_validation(config: AgentConfig, issue, run_id: str, branch: str, started_at: str, log_file: str | None, command_name: str, error_summary: str, planner_result: PlannerResult | None, engine_result=None) -> RunResult:
    mark_failed(config, issue.number)
    if config.comment_on_failure:
        comment_issue(config, issue.number, validation_failed_comment(run_id, command_name, error_summary))
    _write_record(config, issue=issue, run_id=run_id, branch=branch, status="failed", pr_url=None, started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, engine_result=engine_result)
    return RunResult("failed", error_summary, issue_number=issue.number, run_id=run_id)


def _write_record(config: AgentConfig, *, issue, run_id: str, branch: str, status: str, pr_url: str | None, started_at: str, finished_at: str | None, log_file: str | None, error_summary: str | None, planner_result: PlannerResult | None, engine_result) -> None:
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
            repo_instructions_enabled=config.enable_repo_instructions,
            repo_instruction_files=config.repo_instructions.files_found if config.repo_instructions else None,
            repo_test_cmd_source="commands.env" if (config.enable_repo_instructions and config.repo_instructions and config.repo_instructions.commands.get("TEST_CMD")) else "main config",
            repo_lint_cmd_source="commands.env" if (config.enable_repo_instructions and config.repo_instructions and config.repo_instructions.commands.get("LINT_CMD")) else "main config",
            engine=config.engine,
            engine_exit_code=engine_result.exit_code if engine_result else None,
            engine_timed_out=engine_result.timed_out if engine_result else False,
            engine_error_summary=engine_result.error_summary if engine_result else None,
        ),
    )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# Rev 08: PR follow-up orchestrator
FollowupStatus = Literal["no_followup", "no_changes", "pr_updated", "failed", "blocked"]


@dataclass(frozen=True)
class FollowupResult:
    status: FollowupStatus
    message: str
    pr_number: int | None = None
    run_id: str | None = None
    commit_sha: str | None = None


def run_pr_followup_once(config: AgentConfig) -> FollowupResult:
    if not config.enable_pr_followups:
        return FollowupResult("no_followup", "PR follow-ups disabled")

    lock = FileLock(config.lock_file, stale_seconds=config.stale_lock_seconds)
    try:
        lock.acquire()
    except LockAlreadyHeld as exc:
        return FollowupResult("blocked", str(exc))

    task = None
    run_id = None
    started_at = _now_iso()
    log_file = None
    planner_result: PlannerResult | None = None
    ci_context: CIContext | None = None
    engine_result = None

    try:
        task = find_pending_followup(config)
        if task is None:
            return FollowupResult("no_followup", "No pending follow-up commands")

        run_id = f"run-{started_at.replace(':', '').replace('-', '')}-pr-{task.pr_number}-{task.comment_id[:8]}"
        run_id = run_id.replace("T", "-")

        accept_followup_comment(config, task, run_id)

        if config.comment_on_start:
            comment_pr(config, task.pr_number, followup_started_comment(run_id, task.command_text))

        add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_running)

        stage = "checkout_pr_branch"
        checkout_existing_branch(config.repo_path, task.head_branch, task.base_branch)

        # Collect CI context if this is a CI fix
        if task.is_ci_fix and config.enable_ci_context:
            stage = "collect_ci_context"
            if config.comment_on_start:
                comment_pr(config, task.pr_number, ci_context_collecting_comment(run_id, task.ci_command_alias or "fix-ci"))
            ci_context = build_ci_context(config, task.pr_number)
            
            # Check if we should require failing checks
            if config.ci_require_failed_checks and not ci_context.failing_checks_found:
                remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
                if config.comment_on_failure:
                    comment_pr(config, task.pr_number, ci_context_no_failing_checks_comment(run_id))
                _write_followup_record(
                    config, task=task, run_id=run_id, branch=task.head_branch, 
                    status="no_failed_checks", started_at=started_at, finished_at=_now_iso(),
                    log_file=log_file, error_summary="No failing checks found (CI_REQUIRE_FAILED_CHECKS=true)",
                    planner_result=planner_result, commit_sha=None,
                    is_ci_fix=True, ci_checks_found=ci_context.checks_found,
                    ci_failing_checks_found=ci_context.failing_checks_found,
                    ci_failed_check_names=ci_context.failed_check_names,
                    ci_context_summary=ci_context.summary,
                    ci_log_excerpt=ci_context.log_excerpt,
                    ci_warnings=ci_context.warnings,
                )
                mark_comment_processed(config, task)
                return FollowupResult("no_failed_checks", "No failing checks found (CI_REQUIRE_FAILED_CHECKS=true)", pr_number=task.pr_number, run_id=run_id)
            
            if not ci_context.checks_found:
                if config.comment_on_start:
                    comment_pr(config, task.pr_number, ci_context_no_checks_comment(run_id))

        stage = "planner"
        if config.enable_planner:
            if config.comment_plan:
                comment_pr(config, task.pr_number, planner_started_comment(run_id))
            repo_instruction_files = config.repo_instructions.files_found if config.repo_instructions else None
            context = build_repo_context(config.repo_path, max_files=config.repo_context_max_files, max_bytes=config.repo_context_max_bytes, repo_instruction_files=repo_instruction_files)
            planner_result = run_planner(config, task, context, run_id, repo_instructions=config.repo_instructions)
            if config.comment_plan and config.enable_planner:
                if planner_result and planner_result.ok:
                    comment_pr(config, task.pr_number, planner_completed_comment(run_id, planner_result.summary))
                elif planner_result:
                    comment_pr(config, task.pr_number, planner_failed_comment(run_id, planner_result.error))

        implementation_prompt = build_followup_prompt(task=task, run_id=run_id, planner_result=planner_result, ci_context=ci_context, repo_instructions=config.repo_instructions)

        stage = "run_engine"
        engine = get_engine(config)
        prompt_file = config.run_dir / f"{run_id}-prompt.md"
        log_file = config.log_dir / f"{run_id}.log"
        prompt_file.write_text(implementation_prompt)
        
        request = EngineRequest(
            run_id=run_id,
            repo_path=config.repo_path,
            prompt_file=prompt_file,
            prompt_text=implementation_prompt,
            model=config.model,
            log_file=log_file,
            timeout_seconds=config.engine_timeout_seconds,
            mode="pr_followup",
        )
        engine_result = engine.run(request)
        log_file = str(engine_result.log_file)
        if engine_result.timed_out:
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            if config.comment_on_failure:
                comment_pr(config, task.pr_number, followup_failed_comment(run_id, task.command_text, "run_engine", f"Engine timed out after {config.engine_timeout_seconds} seconds"))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="failed", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=f"Engine timed out after {config.engine_timeout_seconds} seconds", planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("failed", f"Engine timed out after {config.engine_timeout_seconds} seconds", pr_number=task.pr_number, run_id=run_id)
        if not engine_result.ok:
            error_summary = engine_result.error_summary or f"Engine exited with code {engine_result.exit_code}"
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            if config.comment_on_failure:
                if task.is_ci_fix:
                    comment_pr(config, task.pr_number, ci_fix_failed_comment(run_id, task.command_text, "run_engine", error_summary))
                else:
                    comment_pr(config, task.pr_number, followup_failed_comment(run_id, task.command_text, "run_engine", error_summary))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="failed", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("failed", error_summary, pr_number=task.pr_number, run_id=run_id)

        stage = "check_changes"
        if not has_changes(config.repo_path):
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            if config.comment_on_no_changes:
                comment_pr(config, task.pr_number, followup_no_changes_comment(run_id, task.command_text))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="no_changes", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("no_changes", "Engine produced no changes.", pr_number=task.pr_number, run_id=run_id)

        stage = "safety"
        safety = check_safety(config)
        if not safety.ok:
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            comment_pr(config, task.pr_number, followup_blocked_comment(run_id, task.command_text, safety.reason or "safety_failed", safety.details))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="blocked", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=f"{safety.reason}: {'; '.join(safety.details[:3])}", planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("blocked", f"{safety.reason}: {'; '.join(safety.details[:3])}", pr_number=task.pr_number, run_id=run_id)

        stage = "lint"
        validation = _run_validation(config, config.lint_cmd, "lint")
        if validation is not None:
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            if config.comment_on_failure:
                comment_pr(config, task.pr_number, followup_failed_comment(run_id, task.command_text, "lint", validation))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="failed", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=validation, planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("failed", validation, pr_number=task.pr_number, run_id=run_id)

        stage = "test"
        validation = _run_validation(config, config.test_cmd, "test")
        if validation is not None:
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            if config.comment_on_failure:
                comment_pr(config, task.pr_number, followup_failed_comment(run_id, task.command_text, "test", validation))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="failed", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=validation, planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("failed", validation, pr_number=task.pr_number, run_id=run_id)

        stage = "commit"
        commit_message = f"agent: follow up on PR #{task.pr_number}"
        commit_all(config.repo_path, commit_message)
        commit_sha = current_commit(config.repo_path)

        stage = "push"
        push_branch(config.repo_path, task.head_branch)

        remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
        add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_done)
        if config.comment_on_success:
            if task.is_ci_fix:
                comment_pr(config, task.pr_number, ci_fix_pushed_comment(run_id, task.command_text, commit_sha, task.pr_url))
            else:
                comment_pr(config, task.pr_number, followup_pushed_comment(run_id, task.command_text, commit_sha, task.pr_url))
        _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="pr_updated", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=None, planner_result=planner_result, commit_sha=commit_sha, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
        mark_comment_processed(config, task)
        return FollowupResult("pr_updated", f"Pushed follow-up commit {commit_sha[:8]} to PR #{task.pr_number}", pr_number=task.pr_number, run_id=run_id, commit_sha=commit_sha)

    except Exception as exc:
        error_summary = short_error(exc)
        if task is not None and run_id is not None:
            remove_label_from_pr_or_issue(config, task.pr_number, config.label_followup_running)
            add_label_to_pr_or_issue(config, task.pr_number, config.label_followup_failed)
            if config.comment_on_failure:
                if task.is_ci_fix:
                    comment_pr(config, task.pr_number, ci_fix_failed_comment(run_id, task.command_text, stage, error_summary))
                else:
                    comment_pr(config, task.pr_number, followup_failed_comment(run_id, task.command_text, stage, error_summary))
            _write_followup_record(config, task=task, run_id=run_id, branch=task.head_branch, status="failed", started_at=started_at, finished_at=_now_iso(), log_file=log_file, error_summary=error_summary, planner_result=planner_result, commit_sha=None, is_ci_fix=task.is_ci_fix, ci_checks_found=ci_context.checks_found if ci_context else False, ci_failing_checks_found=ci_context.failing_checks_found if ci_context else False, ci_failed_check_names=ci_context.failed_check_names if ci_context else None, ci_context_summary=ci_context.summary if ci_context else None, ci_log_excerpt=ci_context.log_excerpt if ci_context else None, ci_warnings=ci_context.warnings if ci_context else None, engine_result=engine_result)
            mark_comment_processed(config, task)
            return FollowupResult("failed", error_summary, pr_number=task.pr_number, run_id=run_id)
        return FollowupResult("failed", error_summary)
    finally:
        lock.release()


def _write_followup_record(
    config: AgentConfig,
    *,
    task: FollowupTask,
    run_id: str,
    branch: str,
    status: str,
    started_at: str,
    finished_at: str | None,
    log_file: str | None,
    error_summary: str | None,
    planner_result: PlannerResult | None,
    commit_sha: str | None,
    is_ci_fix: bool = False,
    ci_checks_found: bool = False,
    ci_failing_checks_found: bool = False,
    ci_failed_check_names: list[str] | None = None,
    ci_context_summary: str | None = None,
    ci_log_excerpt: str | None = None,
    ci_warnings: list[str] | None = None,
    engine_result=None,
) -> None:
    # Save CI log excerpt to separate file if it's large
    ci_log_excerpt_file = None
    if ci_log_excerpt and len(ci_log_excerpt) > 1000:
        ci_log_path = config.run_dir / f"{run_id}-ci-context.md"
        ci_log_path.write_text(ci_log_excerpt)
        ci_log_excerpt_file = str(ci_log_path)
    
    write_run_record(
        config.run_record_dir,
        RunRecord(
            run_id=run_id,
            issue_number=0,
            issue_title="",
            owner_repo=config.owner_repo,
            model=config.model,
            base_branch=task.base_branch,
            agent_branch=branch,
            status=status,
            pr_url=task.pr_url,
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
            run_type="pr_followup",
            pr_number=task.pr_number,
            pr_title=task.pr_title,
            comment_id=task.comment_id,
            command_text=task.command_text,
            commit_sha=commit_sha,
            is_ci_fix=is_ci_fix,
            ci_checks_found=ci_checks_found,
            ci_failing_checks_found=ci_failing_checks_found,
            ci_failed_check_names=ci_failed_check_names,
            ci_context_summary=ci_context_summary,
            ci_log_excerpt=ci_log_excerpt,
            ci_log_excerpt_file=ci_log_excerpt_file,
            ci_warnings=ci_warnings,
            repo_instructions_enabled=config.enable_repo_instructions,
            repo_instruction_files=config.repo_instructions.files_found if config.repo_instructions else None,
            repo_test_cmd_source="commands.env" if (config.enable_repo_instructions and config.repo_instructions and config.repo_instructions.commands.get("TEST_CMD")) else "main config",
            repo_lint_cmd_source="commands.env" if (config.enable_repo_instructions and config.repo_instructions and config.repo_instructions.commands.get("LINT_CMD")) else "main config",
            engine=config.engine,
            engine_exit_code=engine_result.exit_code if engine_result else None,
            engine_timed_out=engine_result.timed_out if engine_result else False,
            engine_error_summary=engine_result.error_summary if engine_result else None,
        ),
    )
