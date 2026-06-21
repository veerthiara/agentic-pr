from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agentic_pr.command import run
from agentic_pr.comment_state import is_processed, mark_processed
from agentic_pr.config import AgentConfig


@dataclass(frozen=True)
class FollowupTask:
    pr_number: int
    pr_title: str
    comment_id: str
    comment_author: str
    comment_body: str
    command_text: str
    head_branch: str
    base_branch: str
    pr_url: str
    is_ci_fix: bool = False
    ci_command_alias: str | None = None


def find_pending_followup(config: AgentConfig) -> FollowupTask | None:
    if not config.enable_pr_followups:
        return None

    prs = _list_open_prs(config)
    for pr in prs:
        if config.pr_followup_require_label:
            labels = [label["name"] for label in pr.get("labels", [])]
            if config.label_followup not in labels:
                continue

        details = _get_pr_details(config, pr["number"])
        if not details:
            continue

        comments = details.get("comments", [])
        for comment in comments:
            body = comment.get("body", "")
            comment_id = str(comment.get("id", ""))
            author = comment.get("author", {}).get("login", "unknown")

            if not body.startswith(config.pr_followup_command_prefix):
                continue

            if is_processed(config, pr["number"], comment_id):
                continue

            if _is_bot(author):
                continue

            command_text = body[len(config.pr_followup_command_prefix):].strip()
            if not command_text:
                continue

            # Check if this is a CI-focused command
            is_ci_fix = False
            ci_command_alias = None
            for alias in config.ci_command_aliases:
                if body.strip().startswith(alias):
                    is_ci_fix = True
                    ci_command_alias = alias
                    break

            return FollowupTask(
                pr_number=pr["number"],
                pr_title=pr["title"],
                comment_id=comment_id,
                comment_author=author,
                comment_body=body,
                command_text=command_text,
                head_branch=details["headRefName"],
                base_branch=details["baseRefName"],
                pr_url=details.get("url", ""),
                is_ci_fix=is_ci_fix,
                ci_command_alias=ci_command_alias,
            )

    return None


def _list_open_prs(config: AgentConfig) -> list[dict]:
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


def _get_pr_details(config: AgentConfig, pr_number: int) -> dict | None:
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


def _is_bot(author: str) -> bool:
    return author.endswith("[bot]") or author in {"github-actions", "dependabot", "renovate"}


def accept_followup_comment(config: AgentConfig, task: FollowupTask, run_id: str) -> None:
    body = (
        f"Follow-up command accepted.\n\n"
        f"Run ID: `{run_id}`\n"
        f"Command: `{task.command_text}`\n"
        f"Author: @{task.comment_author}"
    )
    run(
        [
            "gh",
            "pr",
            "comment",
            str(task.pr_number),
            "--repo",
            config.owner_repo,
            "--body",
            body,
        ]
    )


def mark_comment_processed(config: AgentConfig, task: FollowupTask) -> None:
    mark_processed(config, task.pr_number, task.comment_id)