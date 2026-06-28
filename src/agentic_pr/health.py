from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agentic_pr.command import CommandResult, run
from agentic_pr.config import AgentConfig
from agentic_pr.engine import get_engine
from agentic_pr.lock import FileLock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str  # "ok", "warn", "fail"
    message: str


@dataclass(frozen=True)
class HealthSummary:
    checks: List[HealthCheck]
    overall_status: str  # "ok", "warn", "fail"
    engine_name: str | None = None
    engine_status: str | None = None
    engine_experimental: bool = False
    latest_run: dict | None = None


def _check_config(config: AgentConfig) -> HealthCheck:
    """Check that config loads correctly."""
    try:
        # Just verify the basic fields are present
        if not config.repo_path or not config.owner_repo:
            return HealthCheck("config", "fail", "Missing required config values")
        return HealthCheck("config", "ok", "Config loaded successfully")
    except Exception as exc:
        return HealthCheck("config", "fail", f"Config error: {exc}")


def _check_repo_path(config: AgentConfig) -> HealthCheck:
    """Check that repo path exists and is a directory."""
    if not config.repo_path.exists():
        return HealthCheck("repo_path", "fail", f"Repo path does not exist: {config.repo_path}")
    if not config.repo_path.is_dir():
        return HealthCheck("repo_path", "fail", f"Repo path is not a directory: {config.repo_path}")
    return HealthCheck("repo_path", "ok", f"Repo path exists: {config.repo_path}")


def _check_git_repo(config: AgentConfig) -> HealthCheck:
    """Check that repo path is a git repository."""
    try:
        result = run(["git", "rev-parse", "--git-dir"], cwd=config.repo_path, check=False)
        if result.returncode != 0:
            return HealthCheck("git_repo", "fail", f"Repo is not a git repository: {config.repo_path}")
        return HealthCheck("git_repo", "ok", "Repo is a git repository")
    except Exception as exc:
        return HealthCheck("git_repo", "fail", f"Git check failed: {exc}")


def _check_working_tree(config: AgentConfig) -> HealthCheck:
    """Check working tree status."""
    try:
        result = run(["git", "status", "--porcelain"], cwd=config.repo_path, check=False)
        if result.returncode != 0:
            return HealthCheck("working_tree", "fail", f"Git status failed: {result.stderr}")
        
        if result.stdout.strip():
            return HealthCheck("working_tree", "warn", f"Working tree has changes:\n{result.stdout[:200]}")
        return HealthCheck("working_tree", "ok", "Working tree is clean")
    except Exception as exc:
        return HealthCheck("working_tree", "fail", f"Working tree check failed: {exc}")


def _check_gh_exists() -> HealthCheck:
    """Check that gh command exists."""
    try:
        result = run(["which", "gh"], check=False)
        if result.returncode != 0:
            return HealthCheck("gh", "fail", "gh command not found")
        return HealthCheck("gh", "ok", "gh command available")
    except Exception as exc:
        return HealthCheck("gh", "fail", f"gh check failed: {exc}")


def _check_gh_auth(config: AgentConfig) -> HealthCheck:
    """Check that gh auth status works."""
    try:
        result = run(["gh", "auth", "status"], check=False, timeout=10)
        if result.returncode != 0:
            return HealthCheck("gh_auth", "fail", f"gh auth failed: {result.stderr}")
        return HealthCheck("gh_auth", "ok", "gh auth successful")
    except Exception as exc:
        return HealthCheck("gh_auth", "fail", f"gh auth check failed: {exc}")


def _check_owner_repo(config: AgentConfig) -> HealthCheck:
    """Check that owner/repo is accessible."""
    try:
        # This is a basic check - we can't easily verify without network
        if not config.owner_repo or "/" not in config.owner_repo:
            return HealthCheck("owner_repo", "fail", "Invalid owner/repo format")
        return HealthCheck("owner_repo", "ok", f"Owner/repo valid: {config.owner_repo}")
    except Exception as exc:
        return HealthCheck("owner_repo", "fail", f"Owner/repo check failed: {exc}")


def _check_ollama(config: AgentConfig) -> HealthCheck:
    """Check that Ollama API responds using the CLI."""
    try:
        result = run(["ollama", "list"], check=False, timeout=5)
        if result.returncode != 0:
            return HealthCheck("ollama", "fail", f"Ollama CLI error: {result.stderr or result.stdout}")
        return HealthCheck("ollama", "ok", "Ollama responsive")
    except Exception as exc:
        return HealthCheck("ollama", "fail", f"Ollama check failed: {exc}")


def _check_launchd_service(config: AgentConfig) -> HealthCheck:
    """Check launchd service status if on macOS."""
    try:
        # Only check on macOS
        if os.name != 'posix':
            return HealthCheck("launchd", "ok", "Not on macOS, skipping")
            
        if not config.service_label:
            return HealthCheck("launchd", "warn", "No service label configured")
            
        # launchctl print requires the full domain path
        uid = os.getuid()
        domain = f"gui/{uid}/{config.service_label}"
        result = run(["launchctl", "print", domain], check=False)
        if result.returncode != 0:
            return HealthCheck("launchd", "fail", f"Service not found: {config.service_label}")
        return HealthCheck("launchd", "ok", f"Service running: {config.service_label}")
    except Exception as exc:
        return HealthCheck("launchd", "fail", f"Launchd check failed: {exc}")


def _check_lock_file(config: AgentConfig) -> HealthCheck:
    """Check lock file status."""
    try:
        if not config.lock_file.exists():
            return HealthCheck("lock_file", "ok", "No lock file (not running)")
        
        lock = FileLock(config.lock_file)
        if lock._is_stale():
            return HealthCheck("lock_file", "warn", f"Stale lock file: {config.lock_file}")
        else:
            return HealthCheck("lock_file", "ok", "Active lock file")
    except Exception as exc:
        return HealthCheck("lock_file", "fail", f"Lock check failed: {exc}")


def _check_engine(config: AgentConfig) -> HealthCheck:
    """Check engine availability."""
    try:
        engine = get_engine(config)
        result = engine.doctor(config)
        return HealthCheck(f"engine_{result.name}", result.status, result.message)
    except Exception as exc:
        return HealthCheck("engine", "fail", f"Engine check failed: {exc}")


def get_health_summary(config: AgentConfig) -> HealthSummary:
    """Get a comprehensive health summary."""
    engine_name = getattr(config, "engine", "aider")
    checks = [
        _check_config(config),
        _check_repo_path(config),
        _check_git_repo(config),
        _check_working_tree(config),
        _check_gh_exists(),
        _check_gh_auth(config),
        _check_owner_repo(config),
        _check_ollama(config),
        _check_launchd_service(config),
        _check_lock_file(config),
        _check_engine(config),
    ]
    
    # Determine overall status
    overall_status = "ok"
    for check in checks:
        if check.status == "fail":
            overall_status = "fail"
            break
        elif check.status == "warn" and overall_status == "ok":
            overall_status = "warn"
    
    engine_check = next((check for check in checks if check.name.startswith("engine")), None)
    return HealthSummary(
        checks=checks,
        overall_status=overall_status,
        engine_name=engine_name,
        engine_status=engine_check.status if engine_check else None,
        engine_experimental=bool(getattr(config, "openhands_experimental", False) and engine_name == "openhands"),
    )
