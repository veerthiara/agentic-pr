from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from agentic_pr.config import AgentConfig


@dataclass
class CommentState:
    owner_repo: str
    pr_number: int
    processed_comment_ids: list[str]
    updated_at: str


def _state_file(config: AgentConfig, pr_number: int) -> Path:
    config.comment_state_dir.mkdir(parents=True, exist_ok=True)
    safe_repo = config.owner_repo.replace("/", "_")
    return config.comment_state_dir / f"{safe_repo}_pr{pr_number}.json"


def load_comment_state(config: AgentConfig, pr_number: int) -> CommentState:
    path = _state_file(config, pr_number)
    if not path.exists():
        return CommentState(
            owner_repo=config.owner_repo,
            pr_number=pr_number,
            processed_comment_ids=[],
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
    data = json.loads(path.read_text())
    return CommentState(
        owner_repo=data.get("owner_repo", config.owner_repo),
        pr_number=data.get("pr_number", pr_number),
        processed_comment_ids=data.get("processed_comment_ids", []),
        updated_at=data.get("updated_at", datetime.now().isoformat(timespec="seconds")),
    )


def is_processed(config: AgentConfig, pr_number: int, comment_id: str) -> bool:
    state = load_comment_state(config, pr_number)
    return comment_id in state.processed_comment_ids


def mark_processed(config: AgentConfig, pr_number: int, comment_id: str) -> None:
    state = load_comment_state(config, pr_number)
    if comment_id not in state.processed_comment_ids:
        state.processed_comment_ids.append(comment_id)
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        path = _state_file(config, pr_number)
        path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True) + "\n")