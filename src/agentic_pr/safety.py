from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath

from agentic_pr.config import AgentConfig
from agentic_pr.git_ops import changed_files, diff_line_count


@dataclass(frozen=True)
class SafetyResult:
    ok: bool
    reason: str | None
    details: list[str]


def path_is_blocked(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    for pattern in patterns:
        pat = pattern.strip().replace("\\", "/")
        if not pat:
            continue
        if fnmatch(normalized, pat) or fnmatch(pure.name, pat) or pure.match(pat):
            return True
        if pat.endswith("/*") and normalized.startswith(pat[:-1]):
            return True
    return False


def check_safety(config: AgentConfig) -> SafetyResult:
    files = changed_files(config.repo_path)
    blocked = [path for path in files if path_is_blocked(path, config.blocked_path_patterns)]
    if blocked:
        return SafetyResult(False, "blocked_path", [f"Blocked path: {path}" for path in blocked])
    if len(files) > config.max_changed_files:
        return SafetyResult(False, "too_many_files", [f"Changed files: {len(files)} > {config.max_changed_files}"])
    lines = diff_line_count(config.repo_path)
    if lines > config.max_diff_lines:
        return SafetyResult(False, "diff_too_large", [f"Diff lines: {lines} > {config.max_diff_lines}"])
    return SafetyResult(True, None, [f"Changed files: {len(files)}", f"Diff lines: {lines}"])
