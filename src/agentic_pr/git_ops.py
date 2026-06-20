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


def changed_files(repo_path: Path) -> list[str]:
    files: list[str] = []
    for line in run(["git", "status", "--porcelain"], cwd=repo_path).stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))


def diff_line_count(repo_path: Path) -> int:
    count = 0
    result = run(["git", "diff", "--numstat"], cwd=repo_path)
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        for value in parts[:2]:
            if value.isdigit():
                count += int(value)
    untracked = set(run(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo_path).stdout.splitlines())
    for path in changed_files(repo_path):
        full_path = repo_path / path
        if full_path.exists() and path in untracked:
            try:
                count += len(full_path.read_text(errors="ignore").splitlines())
            except OSError:
                count += 1
    return count


def diff_summary(repo_path: Path, max_lines: int = 40) -> str:
    output = run(["git", "diff", "--stat"], cwd=repo_path).stdout.strip()
    lines = output.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines] + ["..."])
    return output


def commit_all(repo_path: Path, message: str) -> None:
    run(["git", "add", "-A"], cwd=repo_path)
    run(["git", "commit", "-m", message], cwd=repo_path)


def push_branch(repo_path: Path, branch_name_value: str) -> None:
    run(["git", "push", "-u", "origin", branch_name_value], cwd=repo_path)
