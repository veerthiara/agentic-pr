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
