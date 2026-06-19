from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agentic_pr.command import run


def branch_name(issue_number: int, timestamp: str | None = None) -> str:
    suffix = timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
    return f"agent/issue-{issue_number}-{suffix}"


def ensure_git_repo(repo_path: Path) -> None:
    run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_path)


def ensure_clean_worktree(repo_path: Path) -> None:
    status = run(["git", "status", "--porcelain"], cwd=repo_path).stdout.strip()
    if status:
        raise RuntimeError(f"Working tree is not clean:\n{status}")


def checkout_base_and_reset(repo_path: Path, base_branch: str) -> None:
    run(["git", "checkout", base_branch], cwd=repo_path)
    run(["git", "pull", "--ff-only", "origin", base_branch], cwd=repo_path)


def create_branch(repo_path: Path, name: str) -> None:
    run(["git", "checkout", "-b", name], cwd=repo_path)


def has_changes(repo_path: Path) -> bool:
    return bool(run(["git", "status", "--porcelain"], cwd=repo_path).stdout.strip())


def commit_all(repo_path: Path, message: str) -> None:
    run(["git", "add", "-A"], cwd=repo_path)
    run(["git", "commit", "-m", message], cwd=repo_path)


def push_branch(repo_path: Path, branch_name_value: str) -> None:
    run(["git", "push", "-u", "origin", branch_name_value], cwd=repo_path)
