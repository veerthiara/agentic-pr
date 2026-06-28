from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_pr.repo_instructions import RepoInstructions


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
    label_no_changes: str
    label_blocked: str
    ollama_api_base: str
    aider_extra_args: tuple[str, ...]
    log_dir: Path
    run_dir: Path
    poll_interval_seconds: int
    lock_file: Path
    run_record_dir: Path
    agent_host_label: str
    comment_on_start: bool
    comment_on_success: bool
    comment_on_failure: bool
    comment_on_no_changes: bool
    aider_timeout_seconds: int
    max_changed_files: int
    max_diff_lines: int
    require_aiderignore: bool
    blocked_path_patterns: tuple[str, ...]
    test_cmd: str
    lint_cmd: str
    stale_lock_seconds: int
    enable_planner: bool
    planner_model: str
    repo_context_max_files: int
    repo_context_max_bytes: int
    planner_timeout_seconds: int
    comment_plan: bool
    # Rev 08: PR follow-up
    enable_pr_followups: bool
    pr_followup_command_prefix: str
    pr_followup_require_label: bool
    label_followup: str
    label_followup_running: str
    label_followup_done: str
    label_followup_failed: str
    comment_state_dir: Path
    max_followup_comments_per_cycle: int
    # Rev 09: CI-aware PR follow-up
    enable_ci_context: bool
    ci_command_aliases: tuple[str, ...]
    ci_log_max_lines: int
    ci_log_max_bytes: int
    ci_include_successful_checks: bool
    ci_require_failed_checks: bool
    # Rev 10: Repo instructions
    enable_repo_instructions: bool
    repo_instructions_dir: str
    repo_instructions_max_bytes: int
    # Rev 11: Maintenance and cleanup
    run_retention_days: int = 30
    log_retention_days: int = 30
    prompt_retention_days: int = 30
    comment_state_retention_days: int = 90
    max_log_preview_lines: int = 80
    service_label: str | None = None
    # Rev 13: Coding engine abstraction
    engine: str = "aider"
    engine_timeout_seconds: int = 1800
    openhands_command: str = "openhands"
    openhands_timeout_seconds: int = 3600
    openhands_extra_args: tuple[str, ...] = ()
    openhands_use_json_output: bool = False
    openhands_experimental: bool = False
    openhands_llm_base_url: str = "http://host.docker.internal:11434/v1"
    openhands_api_key: str = "local-llm"
    openhands_docker_image: str = "docker.openhands.dev/openhands/openhands:1.8"
    openhands_persistence_dir: Path | None = None
    repo_instructions: "RepoInstructions | None" = None


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
    resolved_run_dir = _resolve_path(run_dir, repo_path)
    lock_file = Path(values.get("LOCK_FILE", resolved_run_dir / "agent.lock")).expanduser()
    run_record_dir = Path(values.get("RUN_RECORD_DIR", repo_path / "var" / "runs")).expanduser()

    enable_repo_instructions = _bool(values.get("ENABLE_REPO_INSTRUCTIONS", "true"), "ENABLE_REPO_INSTRUCTIONS")
    repo_instructions_dir = values.get("REPO_INSTRUCTIONS_DIR", ".agentic-pr")
    repo_instructions_max_bytes = _positive_int(values.get("REPO_INSTRUCTIONS_MAX_BYTES", "40000"), "REPO_INSTRUCTIONS_MAX_BYTES")

    # Load repo instructions to fill missing commands if enabled
    repo_test_cmd = ""
    repo_lint_cmd = ""
    if enable_repo_instructions:
        from agentic_pr.repo_instructions import load_repo_instructions
        repo_instructions = load_repo_instructions(repo_path, repo_instructions_max_bytes, repo_instructions_dir)
        repo_test_cmd = repo_instructions.commands.get("TEST_CMD", "")
        repo_lint_cmd = repo_instructions.commands.get("LINT_CMD", "")

    test_cmd = values.get("TEST_CMD", "") or repo_test_cmd
    lint_cmd = values.get("LINT_CMD", "") or repo_lint_cmd

    # Rev 11: Maintenance and cleanup
    run_retention_days = _positive_int(values.get("RUN_RETENTION_DAYS", "30"), "RUN_RETENTION_DAYS")
    log_retention_days = _positive_int(values.get("LOG_RETENTION_DAYS", "30"), "LOG_RETENTION_DAYS")
    prompt_retention_days = _positive_int(values.get("PROMPT_RETENTION_DAYS", "30"), "PROMPT_RETENTION_DAYS")
    comment_state_retention_days = _positive_int(values.get("COMMENT_STATE_RETENTION_DAYS", "90"), "COMMENT_STATE_RETENTION_DAYS")
    max_log_preview_lines = _positive_int(values.get("MAX_LOG_PREVIEW_LINES", "80"), "MAX_LOG_PREVIEW_LINES")
    service_label = values.get("SERVICE_LABEL")

    engine = values.get("ENGINE", "aider").lower()
    openhands_timeout_seconds = _positive_int(values.get("OPENHANDS_TIMEOUT_SECONDS", "3600"), "OPENHANDS_TIMEOUT_SECONDS")
    engine_timeout_default = values.get("AIDER_TIMEOUT_SECONDS", "1800")
    if engine == "openhands":
        engine_timeout_default = values.get("OPENHANDS_TIMEOUT_SECONDS", str(openhands_timeout_seconds))
    engine_timeout_seconds = _positive_int(
        values.get("ENGINE_TIMEOUT_SECONDS", engine_timeout_default),
        "ENGINE_TIMEOUT_SECONDS",
    )

    return AgentConfig(
            repo_path=repo_path,
            owner_repo=values["OWNER_REPO"],
            base_branch=values["BASE_BRANCH"],
            model=values["MODEL"],
            label_todo=values["LABEL_TODO"],
            label_running=values["LABEL_RUNNING"],
            label_done=values["LABEL_DONE"],
            label_failed=values["LABEL_FAILED"],
            label_no_changes=values.get("LABEL_NO_CHANGES", "agent-no-changes"),
            label_blocked=values.get("LABEL_BLOCKED", "agent-blocked"),
            ollama_api_base=values["OLLAMA_API_BASE"].rstrip("/"),
            aider_extra_args=tuple(_split_args(values.get("AIDER_EXTRA_ARGS", ""))),
            log_dir=_resolve_path(log_dir, repo_path),
            run_dir=resolved_run_dir,
            poll_interval_seconds=_positive_int(values.get("POLL_INTERVAL_SECONDS", "300"), "POLL_INTERVAL_SECONDS"),
            lock_file=_resolve_path(lock_file, repo_path),
            run_record_dir=_resolve_path(run_record_dir, repo_path),
            agent_host_label=values.get("AGENT_HOST_LABEL", "Mac Studio"),
            comment_on_start=_bool(values.get("COMMENT_ON_START", "true"), "COMMENT_ON_START"),
            comment_on_success=_bool(values.get("COMMENT_ON_SUCCESS", "true"), "COMMENT_ON_SUCCESS"),
            comment_on_failure=_bool(values.get("COMMENT_ON_FAILURE", "true"), "COMMENT_ON_FAILURE"),
            comment_on_no_changes=_bool(values.get("COMMENT_ON_NO_CHANGES", "true"), "COMMENT_ON_NO_CHANGES"),
            aider_timeout_seconds=_positive_int(values.get("AIDER_TIMEOUT_SECONDS", "1800"), "AIDER_TIMEOUT_SECONDS"),
            max_changed_files=_positive_int(values.get("MAX_CHANGED_FILES", "20"), "MAX_CHANGED_FILES"),
            max_diff_lines=_positive_int(values.get("MAX_DIFF_LINES", "800"), "MAX_DIFF_LINES"),
            require_aiderignore=_bool(values.get("REQUIRE_AIDERIGNORE", "true"), "REQUIRE_AIDERIGNORE"),
            blocked_path_patterns=tuple(_csv(values.get("BLOCKED_PATH_PATTERNS", ".env,.env.*,*.pem,*.key,*.p12,*.pfx,secrets/*,credentials/*,node_modules/*,.venv/*,dist/*,build/*,**pycache**/*"))),
            test_cmd=test_cmd,
            lint_cmd=lint_cmd,
            stale_lock_seconds=_positive_int(values.get("STALE_LOCK_SECONDS", "7200"), "STALE_LOCK_SECONDS"),
            enable_planner=_bool(values.get("ENABLE_PLANNER", "true"), "ENABLE_PLANNER"),
            planner_model=values.get("PLANNER_MODEL", values["MODEL"]),
            repo_context_max_files=_positive_int(values.get("REPO_CONTEXT_MAX_FILES", "80"), "REPO_CONTEXT_MAX_FILES"),
            repo_context_max_bytes=_positive_int(values.get("REPO_CONTEXT_MAX_BYTES", "120000"), "REPO_CONTEXT_MAX_BYTES"),
            planner_timeout_seconds=_positive_int(values.get("PLANNER_TIMEOUT_SECONDS", "900"), "PLANNER_TIMEOUT_SECONDS"),
            comment_plan=_bool(values.get("COMMENT_PLAN", "true"), "COMMENT_PLAN"),
            # Rev 08: PR follow-up
            enable_pr_followups=_bool(values.get("ENABLE_PR_FOLLOWUPS", "true"), "ENABLE_PR_FOLLOWUPS"),
            pr_followup_command_prefix=values.get("PR_FOLLOWUP_COMMAND_PREFIX", "/agent"),
            pr_followup_require_label=_bool(values.get("PR_FOLLOWUP_REQUIRE_LABEL", "false"), "PR_FOLLOWUP_REQUIRE_LABEL"),
            label_followup=values.get("LABEL_FOLLOWUP", "agent-followup"),
            label_followup_running=values.get("LABEL_FOLLOWUP_RUNNING", "agent-followup-running"),
            label_followup_done=values.get("LABEL_FOLLOWUP_DONE", "agent-followup-done"),
            label_followup_failed=values.get("LABEL_FOLLOWUP_FAILED", "agent-followup-failed"),
            comment_state_dir=_resolve_path(Path(values.get("COMMENT_STATE_DIR", repo_path / "var" / "comment-state")), repo_path),
            max_followup_comments_per_cycle=_positive_int(values.get("MAX_FOLLOWUP_COMMENTS_PER_CYCLE", "1"), "MAX_FOLLOWUP_COMMENTS_PER_CYCLE"),
            # Rev 09: CI-aware PR follow-up
            enable_ci_context=_bool(values.get("ENABLE_CI_CONTEXT", "true"), "ENABLE_CI_CONTEXT"),
            ci_command_aliases=tuple(_csv(values.get("CI_COMMAND_ALIASES", "/agent fix-ci,/agent fix checks,/agent fix failing tests"))),
            ci_log_max_lines=_positive_int(values.get("CI_LOG_MAX_LINES", "250"), "CI_LOG_MAX_LINES"),
            ci_log_max_bytes=_positive_int(values.get("CI_LOG_MAX_BYTES", "40000"), "CI_LOG_MAX_BYTES"),
            ci_include_successful_checks=_bool(values.get("CI_INCLUDE_SUCCESSFUL_CHECKS", "false"), "CI_INCLUDE_SUCCESSFUL_CHECKS"),
            ci_require_failed_checks=_bool(values.get("CI_REQUIRE_FAILED_CHECKS", "false"), "CI_REQUIRE_FAILED_CHECKS"),
            # Rev 10: Repo instructions
            enable_repo_instructions=enable_repo_instructions,
            repo_instructions_dir=repo_instructions_dir,
            repo_instructions_max_bytes=repo_instructions_max_bytes,
            repo_instructions=repo_instructions if enable_repo_instructions else None,
            # Rev 11: Maintenance and cleanup
            run_retention_days=run_retention_days,
            log_retention_days=log_retention_days,
            prompt_retention_days=prompt_retention_days,
            comment_state_retention_days=comment_state_retention_days,
            max_log_preview_lines=max_log_preview_lines,
            service_label=service_label,
            # Rev 13: Coding engine abstraction
            engine=engine,
            engine_timeout_seconds=engine_timeout_seconds,
            openhands_command=values.get("OPENHANDS_COMMAND", "openhands"),
            openhands_timeout_seconds=openhands_timeout_seconds,
            openhands_extra_args=tuple(_split_args(values.get("OPENHANDS_EXTRA_ARGS", ""))),
            openhands_use_json_output=_bool(values.get("OPENHANDS_USE_JSON_OUTPUT", "false"), "OPENHANDS_USE_JSON_OUTPUT"),
            openhands_experimental=_bool(values.get("OPENHANDS_EXPERIMENTAL", "false"), "OPENHANDS_EXPERIMENTAL"),
            openhands_llm_base_url=values.get("OPENHANDS_LLM_BASE_URL", "http://host.docker.internal:11434/v1"),
            openhands_api_key=values.get("OPENHANDS_API_KEY", "local-llm"),
            openhands_docker_image=values.get("OPENHANDS_DOCKER_IMAGE", "docker.openhands.dev/openhands/openhands:1.8"),
            openhands_persistence_dir=_resolve_path(Path(values.get("OPENHANDS_PERSISTENCE_DIR", ".openhands")), repo_path),
        )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_args(value: str) -> list[str]:
    return shlex.split(value)


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


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


def _bool(value: str, key: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{key} must be true or false")
