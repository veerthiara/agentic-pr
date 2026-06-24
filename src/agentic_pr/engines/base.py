from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class EngineRequest:
    run_id: str
    repo_path: Path
    prompt_file: Path
    prompt_text: Optional[str] = None
    model: str = ""
    log_file: Optional[Path] = None
    timeout_seconds: int = 1800
    env: Optional[dict] = None
    mode: str = "issue"  # "issue", "pr_followup", or "ci_fix"
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class EngineResult:
    engine_name: str
    ok: bool
    exit_code: int
    timed_out: bool
    log_file: Optional[Path]
    stdout_tail: Optional[str] = None
    stderr_tail: Optional[str] = None
    error_summary: Optional[str] = None
    started_at: str = ""
    finished_at: str = ""


@dataclass(frozen=True)
class EngineDoctorResult:
    name: str
    status: str  # "ok", "warn", "fail"
    message: str


class CodingEngine(ABC):
    """Abstract base class for coding engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name (e.g., 'aider')."""
        pass

    @abstractmethod
    def run(self, request: EngineRequest) -> EngineResult:
        """Run the coding engine with the given request."""
        pass

    @abstractmethod
    def doctor(self, config) -> EngineDoctorResult:
        """Check engine health/availability."""
        pass