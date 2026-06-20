from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.github_ops import Issue
from agentic_pr.prompt_builder import build_implementation_prompt


@dataclass(frozen=True)
class AiderResult:
    exit_code: int
    log_file: Path
    timed_out: bool = False


def build_prompt(issue: Issue) -> str:
    return build_implementation_prompt(issue=issue, run_id="manual", planner_result=None)


def run_aider(config: AgentConfig, issue: Issue, run_id: str, prompt: str | None = None) -> AiderResult:
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.run_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = config.run_dir / f"{run_id}-prompt.md"
    log_file = config.log_dir / f"{run_id}.log"
    prompt_file.write_text(prompt or build_prompt(issue))

    args = [
        "aider",
        "--model",
        config.model,
        "--no-auto-commits",
        "--no-dirty-commits",
        "--yes-always",
        "--message-file",
        str(prompt_file),
        *config.aider_extra_args,
    ]
    result = run(args, cwd=config.repo_path, check=False, timeout=config.aider_timeout_seconds)
    timeout_note = ""
    if result.timed_out:
        timeout_note = f"\nAider timed out after {config.aider_timeout_seconds} seconds.\n"
    log_file.write_text(result.stdout + result.stderr + timeout_note)
    return AiderResult(exit_code=result.returncode, log_file=log_file, timed_out=result.timed_out)
