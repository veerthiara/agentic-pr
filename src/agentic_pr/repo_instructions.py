from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RepoInstructions:
    instructions_text: str | None = None
    safety_text: str | None = None
    examples_text: str | None = None
    commands: dict[str, str] = field(default_factory=dict)
    files_found: list[str] = field(default_factory=list)


def load_repo_instructions(repo_path: Path, max_bytes: int, instructions_dir: str = ".agentic-pr") -> RepoInstructions:
    base_dir = repo_path / instructions_dir
    if not base_dir.is_dir():
        return RepoInstructions()

    files_found: list[str] = []
    
    def _read_file(name: str) -> str | None:
        file_path = base_dir / name
        if not file_path.is_file():
            return None
        try:
            # Read first max_bytes + 1 to check if we exceed limit, but we only keep up to max_bytes
            with open(file_path, "rb") as f:
                content = f.read(max_bytes + 1)
            
            text = content[:max_bytes].decode("utf-8", errors="ignore")
            if len(content) > max_bytes:
                text += f"\n\n[Warning: {name} truncated due to size limit of {max_bytes} bytes]"
            
            files_found.append(name)
            return text.strip() or None
        except OSError:
            return None

    instructions_text = _read_file("instructions.md")
    safety_text = _read_file("safety.md")
    examples_text = _read_file("examples.md")
    
    commands: dict[str, str] = {}
    commands_text = _read_file("commands.env")
    if commands_text:
        for line in commands_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                commands[key.strip()] = value.strip()

    return RepoInstructions(
        instructions_text=instructions_text,
        safety_text=safety_text,
        examples_text=examples_text,
        commands=commands,
        files_found=files_found,
    )
