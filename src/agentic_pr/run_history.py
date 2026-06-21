from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from agentic_pr.run_record import RunRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    run_type: str
    status: str
    issue_number: int | None
    pr_number: int | None
    pr_title: str | None
    branch: str
    pr_url: str | None
    model: str
    started_at: str
    finished_at: str | None
    error_summary: str | None


def list_runs(config, limit: int = 20) -> List[RunSummary]:
    """List recent runs sorted by started_at (newest first)."""
    records = []
    if not config.run_record_dir.exists():
        return records
    
    for record_file in sorted(config.run_record_dir.glob("run-*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            data = json.loads(record_file.read_text())
            # Handle older run records that might be missing fields
            if "run_type" not in data:
                data["run_type"] = "issue"
            if "pr_number" not in data:
                data["pr_number"] = None
            if "pr_title" not in data:
                data["pr_title"] = None
            if "pr_url" not in data:
                data["pr_url"] = None
            if "error_summary" not in data:
                data["error_summary"] = None
                
            record = RunRecord(**data)
            records.append(RunSummary(
                run_id=record.run_id,
                run_type=record.run_type,
                status=record.status,
                issue_number=record.issue_number,
                pr_number=record.pr_number,
                pr_title=record.pr_title,
                branch=record.agent_branch,
                pr_url=record.pr_url,
                model=record.model,
                started_at=record.started_at,
                finished_at=record.finished_at,
                error_summary=record.error_summary
            ))
            if len(records) >= limit:
                break
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(f"Skipping invalid run record {record_file}: {exc}")
            continue
    
    return records


def get_run(config, run_id: str) -> RunRecord | None:
    """Get a specific run by ID."""
    record_file = config.run_record_dir / f"{run_id}.json"
    if not record_file.exists():
        return None
        
    try:
        data = json.loads(record_file.read_text())
        # Handle older run records that might be missing fields
        if "run_type" not in data:
            data["run_type"] = "issue"
        if "pr_number" not in data:
            data["pr_number"] = None
        if "pr_title" not in data:
            data["pr_title"] = None
        if "pr_url" not in data:
            data["pr_url"] = None
        if "error_summary" not in data:
            data["error_summary"] = None
            
        return RunRecord(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning(f"Skipping invalid run record {record_file}: {exc}")
        return None


def get_last_run(config) -> RunRecord | None:
    """Get the most recent run."""
    if not config.run_record_dir.exists():
        return None
        
    latest_file = max(config.run_record_dir.glob("run-*.json"), key=lambda f: f.stat().st_mtime, default=None)
    if not latest_file:
        return None
        
    try:
        data = json.loads(latest_file.read_text())
        # Handle older run records that might be missing fields
        if "run_type" not in data:
            data["run_type"] = "issue"
        if "pr_number" not in data:
            data["pr_number"] = None
        if "pr_title" not in data:
            data["pr_title"] = None
        if "pr_url" not in data:
            data["pr_url"] = None
        if "error_summary" not in data:
            data["error_summary"] = None
            
        return RunRecord(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.warning(f"Skipping invalid run record {latest_file}: {exc}")
        return None


def summarize_run(run_record: RunRecord) -> str:
    """Create a human-readable summary of a run."""
    if run_record.run_type == "issue":
        title = f"Issue #{run_record.issue_number}: {run_record.issue_title}"
    else:
        title = f"PR #{run_record.pr_number} ({run_record.pr_title})" if run_record.pr_number else "PR follow-up"
    
    status_text = {
        "pr_created": "✅ PR Created",
        "no_changes": "⚠️ No Changes",
        "failed": "❌ Failed",
        "blocked": "🚫 Blocked",
        "no_issue": "❓ No Issue",
    }.get(run_record.status, run_record.status)
    
    summary_lines = [
        f"Run ID: {run_record.run_id}",
        f"Type: {run_record.run_type}",
        f"Status: {status_text}",
        f"Task: {title}",
        f"Branch: {run_record.agent_branch}",
        f"Model: {run_record.model}",
        f"Started: {run_record.started_at}",
    ]
    
    if run_record.finished_at:
        summary_lines.append(f"Finished: {run_record.finished_at}")
        
    if run_record.pr_url:
        summary_lines.append(f"PR URL: {run_record.pr_url}")
        
    if run_record.error_summary:
        summary_lines.append(f"Error: {run_record.error_summary}")
        
    return "\n".join(summary_lines)