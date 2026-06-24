from __future__ import annotations

import shutil
import urllib.error
import urllib.request

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.engine import get_engine
from agentic_pr.git_ops import ensure_clean_worktree, ensure_git_repo
from agentic_pr.github_ops import ensure_repo_access


def run_doctor(config: AgentConfig, *, strict_clean: bool = True) -> list[str]:
    messages: list[str] = []

    for command in ("gh", "git", "aider"):
        if not shutil.which(command):
            raise RuntimeError(f"Required command not found: {command}")
        messages.append(f"ok: found {command}")

    run(["gh", "auth", "status"])
    messages.append("ok: gh auth status")

    if not config.repo_path.exists():
        raise RuntimeError(f"Repo path does not exist: {config.repo_path}")
    messages.append(f"ok: repo path exists: {config.repo_path}")

    ensure_git_repo(config.repo_path)
    messages.append("ok: repo path is a git repo")

    if strict_clean:
        ensure_clean_worktree(config.repo_path)
        messages.append("ok: working tree clean")

    ensure_repo_access(config)
    messages.append(f"ok: GitHub repo accessible: {config.owner_repo}")

    _check_ollama(config.ollama_api_base)
    messages.append(f"ok: Ollama API reachable: {config.ollama_api_base}")

    # Check engine
    engine = get_engine(config)
    if not shutil.which(engine.name):
        raise RuntimeError(f"Engine command not found: {engine.name}")
    messages.append(f"ok: engine {engine.name} available")

    return messages


def _check_ollama(api_base: str) -> None:
    url = f"{api_base.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status >= 400:
                raise RuntimeError(f"Ollama API returned HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama API is not reachable at {url}: {exc}") from exc
