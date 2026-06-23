from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from agentic_pr.config import parse_env_file

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepoConfigRef:
    name: str
    path: Path
    owner_repo: Optional[str] = None
    repo_path: Optional[Path] = None
    base_branch: Optional[str] = None
    enabled: bool = True


def _is_safe_name(name: str) -> bool:
    """Check if a config name is safe (no spaces, no path traversal)."""
    if not name:
        return False
    if " " in name:
        return False
    if ".." in name:
        return False
    if name.startswith("."):
        return False
    if "/" in name or "\\" in name:
        return False
    # Only alphanumeric, dash, underscore
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))


def _parse_config_ref(config_path: Path) -> Optional[RepoConfigRef]:
    """Parse a config file and return a RepoConfigRef."""
    name = config_path.stem
    
    if not _is_safe_name(name):
        logger.warning(f"Skipping config with unsafe name: {name}")
        return None
    
    try:
        values = parse_env_file(config_path)
    except Exception as exc:
        logger.warning(f"Failed to parse config {config_path}: {exc}")
        return None
    
    owner_repo = values.get("OWNER_REPO")
    repo_path_str = values.get("REPO_PATH")
    base_branch = values.get("BASE_BRANCH")
    enabled_str = values.get("ENABLED", "true")
    enabled = enabled_str.lower() == "true"
    
    repo_path = Path(repo_path_str).expanduser().resolve() if repo_path_str else None
    
    return RepoConfigRef(
        name=name,
        path=config_path,
        owner_repo=owner_repo,
        repo_path=repo_path,
        base_branch=base_branch,
        enabled=enabled
    )


def discover_configs(root_path: Path, include_disabled: bool = False) -> List[RepoConfigRef]:
    """Discover repo config files from config/repos/*.env."""
    repos_dir = root_path / "config" / "repos"
    if not repos_dir.exists() or not repos_dir.is_dir():
        return []
    
    configs = []
    for config_file in sorted(repos_dir.glob("*.env")):
        ref = _parse_config_ref(config_file)
        if ref is None:
            continue
        if not ref.enabled and not include_disabled:
            continue
        configs.append(ref)
    
    return configs


def get_config_by_name(root_path: Path, name: str) -> Optional[RepoConfigRef]:
    """Get a specific config by name."""
    if not _is_safe_name(name):
        return None
    
    config_path = root_path / "config" / "repos" / f"{name}.env"
    if not config_path.exists():
        return None
    
    return _parse_config_ref(config_path)


def list_config_summaries(root_path: Path, include_disabled: bool = False) -> List[dict]:
    """Get summary dicts for all configs."""
    configs = discover_configs(root_path, include_disabled=include_disabled)
    return [
        {
            "name": c.name,
            "owner_repo": c.owner_repo,
            "repo_path": str(c.repo_path) if c.repo_path else None,
            "base_branch": c.base_branch,
            "enabled": c.enabled,
            "path": str(c.path),
        }
        for c in configs
    ]