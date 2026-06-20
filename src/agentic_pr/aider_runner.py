from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.github_ops import Issue


@dataclass(frozen=True)
class AiderResult:
    exit_code: int
    log_file: Path


def build_prompt(issue: Issue) -> str:
    return f"""You are a local coding agent working in this git repository.

GitHub issue: #{issue.number}
Title: {issue.title}

User task:
{issue.body}

Rules:
- Make the smallest safe code change that satisfies the issue.
- Do not modify secrets, .env files, credentials, or unrelated generated files.
- Keep the solution simple and readable.
- Add or update tests only if appropriate for this repo.
- Do not merge anything. Only make code changes for a PR.
"""


def run_aider(config: AgentConfig, issue: Issue, run_id: str) -> AiderResult:
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.run_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = config.run_dir / f"{run_id}-prompt.md"
    log_file = config.log_dir / f"{run_id}.log"
    prompt_file.write_text(build_prompt(issue))

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
    result = run(args, cwd=config.repo_path, check=False)
    log_file.write_text(result.stdout + result.stderr)
    return AiderResult(exit_code=result.returncode, log_file=log_file)
