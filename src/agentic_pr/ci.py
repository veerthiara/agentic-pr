from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from agentic_pr.command import run
from agentic_pr.config import AgentConfig


@dataclass(frozen=True)
class CheckResult:
    """Represents a single check result from GitHub PR checks."""
    name: str
    state: str  # "completed", "in_progress", "queued", "pending", "requested", "waiting"
    conclusion: Optional[str]  # "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"
    details_url: Optional[str]
    workflow_run_id: Optional[int]
    check_run_id: Optional[int]
    raw: dict  # Raw JSON for debugging


def get_pr_checks(config: AgentConfig, pr_number: int) -> list[CheckResult]:
    """
    Get all check runs for a PR using gh CLI.
    
    Returns empty list if no checks exist or gh command fails.
    """
    result = run(
        [
            "gh",
            "pr",
            "checks",
            str(pr_number),
            "--repo",
            config.owner_repo,
            "--json",
            "name,state,conclusion,detailsUrl,workflowRunId,checkRunId",
        ],
        check=False,
    )
    
    if result.returncode != 0:
        # No checks found or command failed - return empty list
        return []
    
    try:
        checks_data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    
    checks = []
    for check in checks_data:
        checks.append(CheckResult(
            name=check.get("name", "unknown"),
            state=check.get("state", "unknown"),
            conclusion=check.get("conclusion"),
            details_url=check.get("detailsUrl"),
            workflow_run_id=check.get("workflowRunId"),
            check_run_id=check.get("checkRunId"),
            raw=check,
        ))
    
    return checks


def get_failing_checks(config: AgentConfig, pr_number: int) -> list[CheckResult]:
    """Get only the failing check runs for a PR."""
    all_checks = get_pr_checks(config, pr_number)
    return [
        check for check in all_checks
        if check.conclusion in ("failure", "action_required", "timed_out", "cancelled")
    ]


def has_failing_checks(config: AgentConfig, pr_number: int) -> bool:
    """Check if a PR has any failing checks."""
    failing = get_failing_checks(config, pr_number)
    return len(failing) > 0


def get_workflow_run_logs(config: AgentConfig, run_id: int, max_lines: int = 250, max_bytes: int = 40000) -> str:
    """
    Get logs from a failed workflow run.
    
    Uses 'gh run view --log-failed' to get only failed step logs.
    """
    result = run(
        [
            "gh",
            "run",
            "view",
            str(run_id),
            "--repo",
            config.owner_repo,
            "--log-failed",
        ],
        check=False,
    )
    
    if result.returncode != 0:
        return f"Failed to fetch logs for run {run_id}: {result.stderr}"
    
    logs = result.stdout or ""
    return _truncate_logs(logs, max_lines, max_bytes)


def get_check_run_logs(config: AgentConfig, check_run_id: int, max_lines: int = 250, max_bytes: int = 40000) -> str:
    """
    Get logs from a specific check run.
    
    Uses 'gh api' to fetch check run logs if available.
    """
    result = run(
        [
            "gh",
            "api",
            f"/repos/{config.owner_repo}/check-runs/{check_run_id}/logs",
        ],
        check=False,
    )
    
    if result.returncode != 0:
        return f"Failed to fetch logs for check run {check_run_id}: {result.stderr}"
    
    logs = result.stdout or ""
    return _truncate_logs(logs, max_lines, max_bytes)


def _truncate_logs(logs: str, max_lines: int, max_bytes: int) -> str:
    """Truncate logs to max lines and max bytes."""
    lines = logs.splitlines()
    
    # Truncate by lines
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    else:
        truncated = False
    
    result = "\n".join(lines)
    
    # Truncate by bytes
    if len(result.encode("utf-8")) > max_bytes:
        result = result.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        truncated = True
    
    if truncated:
        result += "\n... [truncated]"
    
    return result