from __future__ import annotations

from datetime import datetime

from agentic_pr.config import AgentConfig


def generate_run_id(issue_number: int, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"run-{timestamp}-issue-{issue_number}"


def status_labels(config: AgentConfig) -> list[str]:
    return [
        config.label_todo,
        config.label_running,
        config.label_done,
        config.label_failed,
        config.label_no_changes,
        config.label_blocked,
    ]


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
        f"- Aider exit code: `{aider_exit_code}`\n\n"
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
