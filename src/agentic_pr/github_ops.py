from __future__ import annotations

import json
from dataclasses import dataclass

from agentic_pr.command import CommandError, run
from agentic_pr.config import AgentConfig


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    created_at: str


LABELS = {
    "todo": ("ededed", "Agent should pick up this issue."),
    "running": ("fbca04", "Agent is currently working on this issue."),
    "done": ("0e8a16", "Agent created a pull request for this issue."),
    "failed": ("b60205", "Agent failed while working on this issue."),
}


def ensure_repo_access(config: AgentConfig) -> None:
    run(["gh", "repo", "view", config.owner_repo, "--json", "nameWithOwner"])


def ensure_labels(config: AgentConfig) -> None:
    existing = _existing_label_names(config)
    wanted = {
        config.label_todo: LABELS["todo"],
        config.label_running: LABELS["running"],
        config.label_done: LABELS["done"],
        config.label_failed: LABELS["failed"],
    }
    for name, (color, description) in wanted.items():
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
    run(
        [
            "gh",
            "issue",
            "edit",
            str(issue_number),
            "--repo",
            config.owner_repo,
            "--add-label",
            config.label_running,
            "--remove-label",
            config.label_todo,
        ]
    )


def mark_done(config: AgentConfig, issue_number: int) -> None:
    run(
        [
            "gh",
            "issue",
            "edit",
            str(issue_number),
            "--repo",
            config.owner_repo,
            "--remove-label",
            config.label_running,
            "--add-label",
            config.label_done,
        ]
    )


def mark_failed(config: AgentConfig, issue_number: int) -> None:
    run(
        [
            "gh",
            "issue",
            "edit",
            str(issue_number),
            "--repo",
            config.owner_repo,
            "--remove-label",
            config.label_running,
            "--add-label",
            config.label_failed,
        ],
        check=False,
    )


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


def _existing_label_names(config: AgentConfig) -> set[str]:
    try:
        result = run(["gh", "label", "list", "--repo", config.owner_repo, "--limit", "200", "--json", "name"])
    except CommandError:
        return set()
    labels = json.loads(result.stdout or "[]")
    return {label["name"] for label in labels}
