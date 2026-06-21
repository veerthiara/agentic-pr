from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanupItem:
    path: Path
    reason: str
    age_days: float
    category: str


def _get_file_age_days(file_path: Path) -> float:
    """Get the age of a file in days."""
    if not file_path.exists():
        return 0.0
    mtime = file_path.stat().st_mtime
    now = time.time()
    return (now - mtime) / (24 * 3600)


def _should_cleanup_file(file_path: Path, retention_days: float, config) -> bool:
    """Check if a file should be cleaned up based on retention policy."""
    if not file_path.exists():
        return False
    
    # Never delete source files, config files, or important directories
    if str(file_path).startswith(str(config.repo_path)) and (
        file_path.name in ('.gitignore', 'README.md') or 
        str(file_path).endswith(('.env', '.env.*')) or
        str(file_path).endswith(('.lock', 'config/agent-test.env'))
    ):
        return False
    
    # Never delete launchd files, plan files, or the main config directory
    if str(file_path).startswith(str(config.repo_path)) and (
        'launchd' in str(file_path) or 
        'plan' in str(file_path) or
        str(file_path).endswith('config')
    ):
        return False
    
    # Never delete the lock file unless it's stale
    if file_path == config.lock_file:
        try:
            import agentic_pr.lock
            lock = agentic_pr.lock.Lock(file_path)
            if not lock.is_stale():
                return False  # Don't delete active locks
        except Exception:
            pass  # If we can't check, proceed with normal cleanup
    
    age_days = _get_file_age_days(file_path)
    return age_days > retention_days


def plan_cleanup(config) -> List[CleanupItem]:
    """Plan what files to clean up based on retention policies."""
    cleanup_items = []
    
    # Run records
    if config.run_record_dir.exists():
        for record_file in config.run_record_dir.glob("run-*.json"):
            if _should_cleanup_file(record_file, config.run_retention_days, config):
                age_days = _get_file_age_days(record_file)
                cleanup_items.append(CleanupItem(
                    path=record_file,
                    reason="Run record older than retention period",
                    age_days=age_days,
                    category="run_records"
                ))
    
    # Log files
    if config.log_dir.exists():
        for log_file in config.log_dir.glob("*.log"):
            if _should_cleanup_file(log_file, config.log_retention_days, config):
                age_days = _get_file_age_days(log_file)
                cleanup_items.append(CleanupItem(
                    path=log_file,
                    reason="Log file older than retention period",
                    age_days=age_days,
                    category="logs"
                ))
    
    # Prompt files (planner, prompt, ci-context)
    if config.run_dir.exists():
        for prompt_file in config.run_dir.glob("*"):
            if prompt_file.is_file() and (
                prompt_file.name.endswith(('.prompt.md', '.planner.md', '-ci-context.md')) or
                prompt_file.name.endswith(('-planner.md', '-prompt.md'))
            ):
                if _should_cleanup_file(prompt_file, config.prompt_retention_days, config):
                    age_days = _get_file_age_days(prompt_file)
                    cleanup_items.append(CleanupItem(
                        path=prompt_file,
                        reason="Prompt file older than retention period",
                        age_days=age_days,
                        category="prompts"
                    ))
    
    # Comment state files
    if config.comment_state_dir.exists():
        for comment_file in config.comment_state_dir.glob("*.json"):
            if _should_cleanup_file(comment_file, config.comment_state_retention_days, config):
                age_days = _get_file_age_days(comment_file)
                cleanup_items.append(CleanupItem(
                    path=comment_file,
                    reason="Comment state file older than retention period",
                    age_days=age_days,
                    category="comment_states"
                ))
    
    # Sort by age (oldest first)
    cleanup_items.sort(key=lambda x: x.age_days, reverse=True)
    return cleanup_items


def run_cleanup(config, dry_run: bool = True) -> List[CleanupItem]:
    """Execute cleanup of old artifacts."""
    items_to_cleanup = plan_cleanup(config)
    
    if not items_to_cleanup:
        logger.info("No files to clean up")
        return []
    
    if dry_run:
        logger.info("Dry run - would delete the following files:")
        for item in items_to_cleanup:
            logger.info(f"  {item.path} ({item.age_days:.1f} days old) - {item.reason}")
    else:
        deleted_count = 0
        for item in items_to_cleanup:
            try:
                if item.path.is_file():
                    item.path.unlink()
                elif item.path.is_dir():
                    shutil.rmtree(item.path)
                logger.info(f"Deleted: {item.path}")
                deleted_count += 1
            except Exception as exc:
                logger.warning(f"Failed to delete {item.path}: {exc}")
        
        logger.info(f"Cleaned up {deleted_count} files")
    
    return items_to_cleanup