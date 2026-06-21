from __future__ import annotations

import json
from dataclasses import dataclass

from agentic_pr.command import CommandError, run
from agentic_pr.config import AgentConfig
from agentic_pr.status import status_labels


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    created_at: str


LABEL_STYLES = {
    "agent-run": ("ededed", "Agent should pick up this issue."),
    "agent-running": ("fbca04", "Agent is currently working on this issue."),
    "agent-pr-created": ("0e8a16", "Agent created a pull request for this issue."),
    "agent-failed": ("b60205", "Agent failed while working on this issue."),
    "agent-no-changes": ("5319e7", "Agent ran but produced no file changes."),
    "agent-blocked": ("d93f0b", "Agent could not safely continue without intervention."),
    "agent-followup": ("ededed", "PR has a follow-up command for the agent."),
    "agent-followup-running": ("fbca04", "Agent is processing a follow-up command on this PR."),
    "agent-followup-done": ("0e8a16", "Agent completed a follow-up command on this PR."),
    "agent-followup-failed": ("b60205", "Agent failed while processing a follow-up command on this PR."),
}


def ensure_repo_access(config: AgentConfig) -> None:
    run(["gh", "repo", "view", config.owner_repo, "--json", "nameWithOwner"])


def ensure_labels(config: AgentConfig) -> None:
    existing = _existing_label_names(config)
    for name in status_labels(config):
        color, description = LABEL_STYLES.get(name, ("ededed", "Agent status label."))
        if name in existing:
            continue
        run(
            [
                "gh",
                "label",
                "create",
                name,
                "--repo",
                config.owner_repo,
                "--color",
                color,
                "--description",
                description,
            ]
        )


def get_oldest_todo_issue(config: AgentConfig) -> Issue | None:
    result = run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            config.owner_repo,
            "--label",
            config.label_todo,
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,title,body,createdAt",
        ]
    )
    issues = json.loads(result.stdout or "[]")
    if not issues:
        return None
    oldest = sorted(issues, key=lambda item: item["createdAt"])[0]
    return Issue(
        number=int(oldest["number"]),
        title=oldest["title"],
        body=oldest.get("body") or "",
        created_at=oldest["createdAt"],
    )


def add_label(config: AgentConfig, issue_number: int, label: str) -> None:
    run(["gh", "issue", "edit", str(issue_number), "--repo", config.owner_repo, "--add-label", label])


def remove_label(config: AgentConfig, issue_number: int, label: str) -> None:
    run(["gh", "issue", "edit", str(issue_number), "--repo", config.owner_repo, "--remove-label", label])


def set_running(config: AgentConfig, issue_number: int) -> None:
    _set_status_label(config, issue_number, config.label_running)


def mark_done(config: AgentConfig, issue_number: int) -> None:
    _set_status_label(config, issue_number, config.label_done)


def mark_failed(config: AgentConfig, issue_number: int) -> None:
    _set_status_label(config, issue_number, config.label_failed, check=False)


def mark_no_changes(config: AgentConfig, issue_number: int) -> None:
    _set_status_label(config, issue_number, config.label_no_changes, check=False)


def mark_blocked(config: AgentConfig, issue_number: int) -> None:
    _set_status_label(config, issue_number, config.label_blocked, check=False)


def clear_running(config: AgentConfig, issue_number: int) -> None:
    remove_label(config, issue_number, config.label_running)


def comment_issue(config: AgentConfig, issue_number: int, body: str) -> None:
    run(["gh", "issue", "comment", str(issue_number), "--repo", config.owner_repo, "--body", body])


def create_pr(config: AgentConfig, branch: str, title: str, body: str) -> str:
    result = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            config.owner_repo,
            "--base",
            config.base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]
    )
    return result.stdout.strip()


def _set_status_label(config: AgentConfig, issue_number: int, label: str, *, check: bool = True) -> None:
    args = ["gh", "issue", "edit", str(issue_number), "--repo", config.owner_repo, "--add-label", label]
    for existing in status_labels(config):
        if existing != label:
            args.extend(["--remove-label", existing])
    run(args, check=check)


def _existing_label_names(config: AgentConfig) -> set[str]:
    try:
        result = run(["gh", "label", "list", "--repo", config.owner_repo, "--limit", "200", "--json", "name"])
    except CommandError:
        return set()
    labels = json.loads(result.stdout or "[]")
    return {label["name"] for label in labels}


# Rev 08: PR follow-up helpers
def list_open_prs(config: AgentConfig) -> list[dict]:
    result = run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            config.owner_repo,
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,title,headRefName,baseRefName,labels,url",
        ],
        check=False,
    )
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []


def get_pr_details(config: AgentConfig, pr_number: int) -> dict | None:
    result = run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            config.owner_repo,
            "--json",
            "comments,headRefName,baseRefName,title,url",
        ],
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None


def comment_pr(config: AgentConfig, pr_number: int, body: str) -> None:
    run(["gh", "pr", "comment", str(pr_number), "--repo", config.owner_repo, "--body", body])


def add_label_to_pr_or_issue(config: AgentConfig, number: int, label: str) -> None:
    run(["gh", "issue", "edit", str(number), "--repo", config.owner_repo, "--add-label", label])


def remove_label_from_pr_or_issue(config: AgentConfig, number: int, label: str) -> None:
    run(["gh", "issue", "edit", str(number), "--repo", config.owner_repo, "--remove-label", label], check=False)


# Rev 09: CI-aware PR follow-up helpers
def get_pr_checks(config: AgentConfig, pr_number: int) -> list[dict]:
    """Get all check runs for a PR using gh CLI."""
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
        return []
    
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []


def get_workflow_run_logs(config: AgentConfig, run_id: int) -> str:
    """Get logs from a failed workflow run."""
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
    
    return result.stdout or ""
