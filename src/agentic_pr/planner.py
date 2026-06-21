from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.github_ops import Issue
from agentic_pr.pr_followup import FollowupTask
from agentic_pr.repo_context import RepoContext
from agentic_pr.repo_instructions import RepoInstructions


@dataclass(frozen=True)
class PlannerResult:
    ok: bool
    status: str
    output: str
    output_file: Path | None
    summary: str | None
    files_to_modify: list[str]
    files_to_create: list[str]
    test_plan: str | None
    error: str | None = None


PlannerInput = Union[Issue, FollowupTask]


def run_planner(config: AgentConfig, input_obj: PlannerInput, context: RepoContext, run_id: str, repo_instructions: RepoInstructions | None = None) -> PlannerResult:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    output_file = config.run_dir / f"{run_id}-planner.md"
    prompt = _planner_prompt(input_obj, context, repo_instructions)
    planner_model = ollama_cli_model(config.planner_model)
    result = run(["ollama", "run", planner_model], input_text=prompt, check=False, timeout=config.planner_timeout_seconds)
    if result.timed_out:
        output_file.write_text(result.stdout + result.stderr + f"\nPlanner timed out after {config.planner_timeout_seconds} seconds.\n")
        return PlannerResult(False, "timeout", result.stdout, output_file, None, [], [], None, f"planner timed out after {config.planner_timeout_seconds} seconds")
    if result.returncode != 0:
        output_file.write_text(result.stdout + result.stderr)
        return PlannerResult(False, "failed", result.stdout, output_file, None, [], [], None, _clean_error(result.stderr) or f"planner exited {result.returncode}")
    output = result.stdout.strip()
    output_file.write_text(output + "\n")
    return _parse_output(output, output_file)


def ollama_cli_model(model: str) -> str:
    if model.startswith("ollama/"):
        return model.removeprefix("ollama/")
    return model


def _clean_error(text: str, max_length: int = 300) -> str:
    cleaned = _strip_ansi(text)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3] + "..."


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


def save_planner_fallback(config: AgentConfig, run_id: str, message: str) -> Path:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    path = config.run_dir / f"{run_id}-planner.md"
    path.write_text(message + "\n")
    return path


def _planner_prompt(input_obj: PlannerInput, context: RepoContext, repo_instructions: RepoInstructions | None = None) -> str:
    if isinstance(input_obj, Issue):
        title = input_obj.title
        body = input_obj.body
        header = "GitHub issue"
    else:
        title = input_obj.pr_title
        body = f"Follow-up command: {input_obj.command_text}\n\nOriginal PR: #{input_obj.pr_number} ({input_obj.pr_title})"
        header = "PR follow-up command"

    instructions_section = ""
    if repo_instructions:
        parts = []
        if repo_instructions.instructions_text:
            parts.append("Project Instructions:\n" + repo_instructions.instructions_text)
        if repo_instructions.safety_text:
            parts.append("Safety Rules:\n" + repo_instructions.safety_text)
        if repo_instructions.examples_text:
            parts.append("Examples:\n" + repo_instructions.examples_text)
        if parts:
            instructions_section = "\nRepo-Specific Instructions & Guidelines:\n" + "\n\n".join(parts) + "\n"

    return f"""You are planning a code change before Aider implements it.

Return a concise Markdown plan with these headings exactly:
Summary
Assumptions
Repo type guess
Files to inspect
Files likely to modify
Files likely to create
Files likely to delete
Implementation steps
Test plan
Risks
Final implementation prompt for Aider

{header}: {title}
{header} body:
{body}
{instructions_section}
Repository context:
{context.as_text()}
"""


def _parse_output(output: str, output_file: Path) -> PlannerResult:
    summary = _section(output, "Summary") or _first_nonempty_line(output)
    files_to_modify = _list_section(output, "Files likely to modify")
    files_to_create = _list_section(output, "Files likely to create")
    test_plan = _section(output, "Test plan")
    return PlannerResult(True, "completed", output, output_file, summary, files_to_modify, files_to_create, test_plan)


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped
    return None


def _section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().strip("#").strip().lower() == heading.lower():
            start = index + 1
            break
    if start is None:
        return None
    collected: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped and not stripped.startswith("-") and stripped.strip("#").strip().lower() in _HEADINGS:
            break
        if stripped.startswith("#") and stripped.strip("# ").lower() in _HEADINGS:
            break
        collected.append(line)
    value = "\n".join(collected).strip()
    return value or None


def _list_section(text: str, heading: str) -> list[str]:
    section = _section(text, heading) or ""
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if stripped and stripped.lower() not in {"none", "n/a"}:
            items.append(stripped.strip("`"))
    return items


_HEADINGS = {
    "summary",
    "assumptions",
    "repo type guess",
    "files to inspect",
    "files likely to modify",
    "files likely to create",
    "files likely to delete",
    "implementation steps",
    "test plan",
    "risks",
    "final implementation prompt for aider",
}
