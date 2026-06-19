from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex


REQUIRED_FIELDS = (
    "REPO_PATH",
    "OWNER_REPO",
    "BASE_BRANCH",
    "MODEL",
    "LABEL_TODO",
    "LABEL_RUNNING",
    "LABEL_DONE",
    "LABEL_FAILED",
    "OLLAMA_API_BASE",
)


@dataclass(frozen=True)
class AgentConfig:
    repo_path: Path
    owner_repo: str
    base_branch: str
    model: str
    label_todo: str
    label_running: str
    label_done: str
    label_failed: str
    ollama_api_base: str
    aider_extra_args: tuple[str, ...]
    log_dir: Path
    run_dir: Path
    poll_interval_seconds: int
    lock_file: Path


class ConfigError(ValueError):
    pass


def parse_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        raise ConfigError(f"Config file does not exist: {env_path}")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"Invalid config line {line_number}: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f"Invalid empty config key on line {line_number}")
        values[key] = _unquote(value)
    return values


def load_config(path: str | Path) -> AgentConfig:
    values = parse_env_file(path)
    missing = [field for field in REQUIRED_FIELDS if not values.get(field)]
    if missing:
        raise ConfigError(f"Missing required config values: {', '.join(missing)}")

    repo_path = Path(values["REPO_PATH"]).expanduser().resolve()
    log_dir = Path(values.get("LOG_DIR", repo_path / "logs")).expanduser()
    run_dir = Path(values.get("RUN_DIR", repo_path / "var" / "run")).expanduser()
    poll_interval_seconds = _positive_int(values.get("POLL_INTERVAL_SECONDS", "300"), "POLL_INTERVAL_SECONDS")

    resolved_run_dir = _resolve_path(run_dir, repo_path)
    lock_file = Path(values.get("LOCK_FILE", resolved_run_dir / "agent.lock")).expanduser()
    return AgentConfig(
        repo_path=repo_path,
        owner_repo=values["OWNER_REPO"],
        base_branch=values["BASE_BRANCH"],
        model=values["MODEL"],
        label_todo=values["LABEL_TODO"],
        label_running=values["LABEL_RUNNING"],
        label_done=values["LABEL_DONE"],
        label_failed=values["LABEL_FAILED"],
        ollama_api_base=values["OLLAMA_API_BASE"].rstrip("/"),
        aider_extra_args=tuple(_split_args(values.get("AIDER_EXTRA_ARGS", ""))),
        log_dir=_resolve_path(log_dir, repo_path),
        run_dir=resolved_run_dir,
        poll_interval_seconds=poll_interval_seconds,
        lock_file=_resolve_path(lock_file, repo_path),
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_args(value: str) -> list[str]:
    return shlex.split(value)


def _resolve_path(path: Path, repo_path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_path / path).resolve()


def _positive_int(value: str, key: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer") from exc
    if parsed <= 0:
        raise ConfigError(f"{key} must be greater than zero")
    return parsed
