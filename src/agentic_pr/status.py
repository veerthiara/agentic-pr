from __future__ import annotations

from datetime import datetime

from agentic_pr.config import AgentConfig


def generate_run_id(issue_number: int, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"run-{timestamp}-issue-{issue_number}"


def status_labels(config: AgentConfig) -> list[str]:
    labels = [
        config.label_todo,
        config.label_running,
        config.label_done,
        config.label_failed,
        config.label_no_changes,
        config.label_blocked,
    ]
    if config.enable_pr_followups:
        labels.extend([
            config.label_followup,
            config.label_followup_running,
            config.label_followup_done,
            config.label_followup_failed,
        ])
    return labels


def start_comment(config: AgentConfig, run_id: str) -> str:
    return (
        "Local Mac Studio agent started.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Model: `{config.model}`\n"
        f"Base branch: `{config.base_branch}`"
    )


def before_aider_comment(config: AgentConfig, run_id: str) -> str:
    return (
        "Running Aider with local Ollama model.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Model: `{config.model}`"
    )


def pr_created_comment(run_id: str, pr_url: str, branch: str) -> str:
    return (
        "Local agent created a PR.\n\n"
        f"PR: {pr_url}\n"
        f"Branch: `{branch}`\n"
        f"Run ID: `{run_id}`"
    )


def no_changes_comment(run_id: str) -> str:
    return (
        "Local agent ran but produced no file changes.\n\n"
        f"Run ID: `{run_id}`\n"
        "Possible reasons: the issue was already satisfied, the request was unclear, "
        "or the model decided no safe edit was needed."
    )


def failed_comment(run_id: str, stage: str, error_summary: str) -> str:
    return (
        "Local agent failed.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Stage: `{stage}`\n"
        f"Error: {error_summary}"
    )


def pr_body(
    *,
    config: AgentConfig,
    issue,
    run_id: str,
    branch: str,
    log_file: str,
    aider_exit_code: int,
    planner_enabled: bool = False,
    plan_summary: str | None = None,
) -> str:
    return (
        "This PR was created by the local Mac Studio agent.\n\n"
        f"Linked issue: Closes #{issue.number}\n\n"
        "Run metadata:\n"
        f"- Run ID: `{run_id}`\n"
        f"- Model: `{config.model}`\n"
        f"- Base branch: `{config.base_branch}`\n"
        f"- Agent branch: `{branch}`\n"
        f"- Agent host: `{config.agent_host_label}`\n"
        f"- Aider exit code: `{aider_exit_code}`\n"
        f"- Planner enabled: `{planner_enabled}`\n"
        f"- Plan summary: {plan_summary or 'Not available'}\n\n"
        "Validation reminder:\n"
        "- Review the diff carefully before merging.\n"
        "- Run any project tests that matter for this change.\n"
        "- This PR was not auto-merged.\n\n"
        "Local artifacts:\n"
        f"- Full logs are stored locally at `{log_file}`.\n"
    )


def short_error(exc: BaseException, max_length: int = 500) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def blocked_comment(run_id: str, reason: str, details: list[str]) -> str:
    detail_text = "; ".join(details[:3])
    return (
        "Local agent blocked this run for safety.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Reason: `{reason}`\n"
        f"Details: {detail_text}"
    )


def preflight_blocked_comment(run_id: str, reason: str, details: list[str]) -> str:
    detail_text = "; ".join(details[:3])
    return (
        "Local agent blocked this run during preflight.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Reason: `{reason}`\n"
        f"Details: {detail_text}"
    )


def aider_timeout_comment(run_id: str, timeout_seconds: int) -> str:
    return (
        "Local agent failed because Aider timed out.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Timeout: `{timeout_seconds}` seconds"
    )


def validation_failed_comment(run_id: str, command_name: str, error_summary: str) -> str:
    return (
        "Local agent failed validation before creating a PR.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_name}`\n"
        f"Error: {error_summary}"
    )



def planner_started_comment(run_id: str) -> str:
    return f"Planning repository changes before implementation.\n\nRun ID: `{run_id}`"


def planner_completed_comment(run_id: str, summary: str | None) -> str:
    return (
        "Planner completed.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Summary: {summary or 'No summary provided.'}"
    )


def planner_failed_comment(run_id: str, error: str | None) -> str:
    return (
        "Planner failed, but implementation will continue with the raw issue prompt.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Reason: {error or 'unknown'}"
    )


def implementation_started_comment(run_id: str) -> str:
    return f"Starting implementation with the final Aider prompt.\n\nRun ID: `{run_id}`"


# Rev 08: PR follow-up comment templates
def followup_accepted_comment(run_id: str, command_text: str, author: str) -> str:
    return (
        "Follow-up command accepted.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Author: @{author}"
    )


def followup_started_comment(run_id: str, command_text: str) -> str:
    return (
        "Follow-up implementation started.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`"
    )


def followup_no_changes_comment(run_id: str, command_text: str) -> str:
    return (
        "Follow-up ran but produced no file changes.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        "Possible reasons: the request was already satisfied, unclear, or no safe edit was needed."
    )


def followup_blocked_comment(run_id: str, command_text: str, reason: str, details: list[str]) -> str:
    detail_text = "; ".join(details[:3])
    return (
        "Follow-up blocked for safety.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Reason: `{reason}`\n"
        f"Details: {detail_text}"
    )


def followup_failed_comment(run_id: str, command_text: str, stage: str, error_summary: str) -> str:
    return (
        "Follow-up failed.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Stage: `{stage}`\n"
        f"Error: {error_summary}"
    )


def followup_pushed_comment(run_id: str, command_text: str, commit_sha: str, pr_url: str) -> str:
    return (
        "Follow-up changes pushed to PR.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Commit: `{commit_sha[:8]}`\n"
        f"PR: {pr_url}"
    )


# Rev 09: CI-aware PR follow-up comment templates
def ci_context_collecting_comment(run_id: str, command_alias: str) -> str:
    return (
        "Collecting CI context for follow-up run.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_alias}`"
    )


def ci_context_no_failing_checks_comment(run_id: str) -> str:
    return (
        "No failing checks found for this PR.\n\n"
        f"Run ID: `{run_id}`\n"
        "CI_REQUIRE_FAILED_CHECKS is enabled, so no fix was attempted."
    )


def ci_context_no_checks_comment(run_id: str) -> str:
    return (
        "No GitHub checks found for this PR.\n\n"
        f"Run ID: `{run_id}`\n"
        "Continuing without CI context."
    )


def ci_fix_pushed_comment(run_id: str, command_text: str, commit_sha: str, pr_url: str) -> str:
    return (
        "CI fix pushed to PR.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Commit: `{commit_sha[:8]}`\n"
        f"PR: {pr_url}"
    )


def ci_fix_failed_comment(run_id: str, command_text: str, stage: str, error_summary: str) -> str:
    return (
        "CI fix failed.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`\n"
        f"Stage: `{stage}`\n"
        f"Error: {error_summary}"
    )


def ci_logs_unavailable_comment(run_id: str, command_text: str) -> str:
    return (
        "CI logs unavailable, continuing with available context.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{command_text}`"
    )
