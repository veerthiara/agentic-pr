from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RunRecord:
    run_id: str
    issue_number: int
    issue_title: str
    owner_repo: str
    model: str
    base_branch: str
    agent_branch: str
    status: str
    pr_url: str | None
    started_at: str
    finished_at: str | None
    log_file: str | None
    error_summary: str | None
    planner_enabled: bool = False
    planner_status: str | None = None
    planner_output_file: str | None = None
    plan_summary: str | None = None
    planned_files_to_modify: list[str] | None = None
    planned_files_to_create: list[str] | None = None
    planned_test_plan: str | None = None
    # Rev 08: PR follow-up fields
    run_type: str = "issue"  # "issue" or "pr_followup"
    pr_number: int | None = None
    pr_title: str | None = None
    comment_id: str | None = None
    command_text: str | None = None
    commit_sha: str | None = None
    # Rev 09: CI-aware PR follow-up fields
    is_ci_fix: bool = False
    ci_checks_found: bool = False
    ci_failing_checks_found: bool = False
    ci_failed_check_names: list[str] | None = None
    ci_context_summary: str | None = None
    ci_log_excerpt: str | None = None
    ci_log_excerpt_file: str | None = None
    ci_warnings: list[str] | None = None
    # Rev 10: Repo instructions fields
    repo_instructions_enabled: bool = False
    repo_instruction_files: list[str] | None = None
    repo_test_cmd_source: str | None = None
    repo_lint_cmd_source: str | None = None


def write_run_record(directory: Path, record: RunRecord) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.run_id}.json"
    path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n")
    return path


def list_run_records(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("run-*.json"))


def load_run_record(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def latest_run_record(directory: Path) -> Path | None:
    records = list_run_records(directory)
    return records[-1] if records else None
