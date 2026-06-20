from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IGNORE_DIRS = {".git", "node_modules", ".venv", "dist", "build", "target", ".pytest_cache", ".mypy_cache", "__pycache__"}
PREFERRED_NAMES = {"README.md", "pyproject.toml", "requirements.txt", "package.json", "Makefile", "AGENTS.md", "main.py", "calc.py"}
PREFERRED_PREFIXES = ("src/", "tests/", "app/")
SECRET_NAMES = {".env"}


@dataclass(frozen=True)
class RepoContext:
    repo_path: Path
    branch: str
    top_level_tree: list[str]
    important_files: list[str]
    project_type_hints: list[str]
    excerpts: dict[str, str]

    def as_text(self) -> str:
        parts = [
            f"Repo path: {self.repo_path}",
            f"Branch: {self.branch}",
            "Top-level tree:",
            *[f"- {item}" for item in self.top_level_tree],
            "Project type hints:",
            *[f"- {hint}" for hint in self.project_type_hints],
            "Important files:",
            *[f"- {path}" for path in self.important_files],
            "File excerpts:",
        ]
        for path, excerpt in self.excerpts.items():
            parts.append(f"--- {path} ---")
            parts.append(excerpt)
        return "\n".join(parts)


def build_repo_context(repo_path: Path, *, max_files: int, max_bytes: int) -> RepoContext:
    repo_path = repo_path.resolve()
    branch = _current_branch(repo_path)
    top_level_tree = sorted(path.name + ("/" if path.is_dir() else "") for path in repo_path.iterdir() if not _ignored_path(path.relative_to(repo_path)))
    candidates = _candidate_files(repo_path, max_files=max_files)
    excerpts: dict[str, str] = {}
    used = 0
    for rel in candidates:
        full = repo_path / rel
        try:
            text = full.read_text(errors="ignore")
        except OSError:
            continue
        remaining = max_bytes - used
        if remaining <= 0:
            break
        excerpt = text[: min(len(text), remaining, 4000)]
        excerpts[rel] = excerpt
        used += len(excerpt.encode())
    return RepoContext(repo_path, branch, top_level_tree, candidates, _project_hints(repo_path), excerpts)


def _candidate_files(repo_path: Path, *, max_files: int) -> list[str]:
    files: list[str] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_path)
        rel = rel_path.as_posix()
        if _ignored_path(rel_path) or _secret_path(rel):
            continue
        if path.name in PREFERRED_NAMES or rel.startswith(PREFERRED_PREFIXES):
            files.append(rel)
    return sorted(files, key=_priority)[:max_files]


def _priority(path: str) -> tuple[int, str]:
    name = Path(path).name
    if name in PREFERRED_NAMES:
        return (0, path)
    return (1, path)


def _ignored_path(path: Path) -> bool:
    return any(part in IGNORE_DIRS or "pycache" in part for part in path.parts)


def _secret_path(path: str) -> bool:
    name = Path(path).name
    return name in SECRET_NAMES or name.startswith(".env.")


def _current_branch(repo_path: Path) -> str:
    import subprocess

    result = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, text=True, capture_output=True, check=False)
    return result.stdout.strip() or "unknown"


def _project_hints(repo_path: Path) -> list[str]:
    hints: list[str] = []
    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
        hints.append("python")
    if (repo_path / "package.json").exists():
        hints.append("node")
    if any((repo_path / name).exists() for name in ("main.py", "app.py")):
        hints.append("python app entrypoint")
    if (repo_path / "tests").exists():
        hints.append("has tests")
    return hints or ["unknown"]
