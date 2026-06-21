from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

from agentic_pr.command import CommandError, run
from agentic_pr.config import AgentConfig
from agentic_pr.git_ops import ensure_clean_worktree, ensure_git_repo


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    reason: str | None
    details: list[str]


def run_preflight(config: AgentConfig) -> PreflightResult:
    details: list[str] = []
    if not config.repo_path.exists():
        return PreflightResult(False, "repo_missing", [f"Repo path does not exist: {config.repo_path}"])
    try:
        ensure_git_repo(config.repo_path)
        details.append("repo is git repo")
        ensure_clean_worktree(config.repo_path)
        details.append("working tree clean")
        if config.require_aiderignore and not (config.repo_path / ".aiderignore").exists():
            return PreflightResult(False, "missing_aiderignore", [f"Missing required .aiderignore in {config.repo_path}"])
        if config.enable_repo_instructions:
            if (config.repo_path / config.repo_instructions_dir / "safety.md").is_file():
                details.append(f"repo safety instructions found ({config.repo_instructions_dir}/safety.md)")
        run(["gh", "auth", "status"])
        details.append("gh auth ok")
        _check_ollama(config.ollama_api_base)
        details.append("ollama reachable")
    except (CommandError, RuntimeError) as exc:
        return PreflightResult(False, "preflight_failed", [str(exc)])
    return PreflightResult(True, None, details)


def _check_ollama(api_base: str) -> None:
    url = f"{api_base.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status >= 400:
                raise RuntimeError(f"Ollama API returned HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama API is not reachable at {url}: {exc}") from exc
