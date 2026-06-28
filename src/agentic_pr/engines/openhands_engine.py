from __future__ import annotations

import re
import time

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.engines.base import CodingEngine, EngineDoctorResult, EngineRequest, EngineResult


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class OpenHandsEngine(CodingEngine):
    """Experimental OpenHands engine implementation.

    The CLI surface has changed across OpenHands builds, so this runner probes
    `openhands --help` and chooses a prompt file or prompt text mode
    defensively. The orchestrator still owns git, GitHub, validation, and PR
    creation.
    """

    def __init__(
        self,
        *,
        command: str = "openhands",
        extra_args: tuple[str, ...] = (),
        use_json_output: bool = False,
        llm_base_url: str | None = None,
        api_key: str | None = None,
        docker_image: str | None = None,
        persistence_dir: str | None = None,
    ) -> None:
        self.command = command
        self.extra_args = extra_args
        self.use_json_output = use_json_output
        self.llm_base_url = llm_base_url
        self.api_key = api_key
        self.docker_image = docker_image
        self.persistence_dir = persistence_dir

    @property
    def name(self) -> str:
        return "openhands"

    def run(self, request: EngineRequest) -> EngineResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        request.repo_path.mkdir(parents=True, exist_ok=True)
        request.prompt_file.parent.mkdir(parents=True, exist_ok=True)
        request.prompt_file.write_text(request.prompt_text or "")
        if request.log_file:
            request.log_file.parent.mkdir(parents=True, exist_ok=True)

        help_text = self._read_help_text()
        args = self._build_command(request, help_text)
        env = dict(request.env or {})
        if request.model:
            env.setdefault("LLM_MODEL", request.model)
        if self.llm_base_url:
            env.setdefault("LLM_BASE_URL", self.llm_base_url)
        if self.api_key:
            env.setdefault("LLM_API_KEY", self.api_key)
        if self.docker_image:
            env.setdefault("OPENHANDS_DOCKER_IMAGE", self.docker_image)
        if self.persistence_dir:
            env.setdefault("OPENHANDS_PERSISTENCE_DIR", self.persistence_dir)
        env.setdefault("OPENHANDS_REPO_PATH", str(request.repo_path))
        env.setdefault("OPENHANDS_PROMPT_FILE", str(request.prompt_file))
        result = run(
            args,
            cwd=request.repo_path,
            check=False,
            timeout=request.timeout_seconds,
            env=env,
        )

        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        log_content = result.stdout + result.stderr
        if result.timed_out:
            log_content += f"\nOpenHands timed out after {request.timeout_seconds} seconds.\n"
        if request.log_file:
            request.log_file.write_text(log_content)

        error_summary = None
        if result.timed_out:
            error_summary = f"OpenHands timed out after {request.timeout_seconds} seconds"
        elif result.returncode != 0:
            detail = _summarize_output(result.stderr or result.stdout)
            error_summary = detail or f"OpenHands exited with code {result.returncode}"

        return EngineResult(
            engine_name=self.name,
            ok=result.returncode == 0 and not result.timed_out,
            exit_code=result.returncode,
            timed_out=result.timed_out,
            log_file=request.log_file,
            stdout_tail=result.stdout[-2000:] if result.stdout else None,
            stderr_tail=result.stderr[-2000:] if result.stderr else None,
            error_summary=error_summary,
            started_at=started_at,
            finished_at=finished_at,
        )

    def doctor(self, config: AgentConfig) -> EngineDoctorResult:
        if not config.openhands_experimental:
            return EngineDoctorResult(
                name=self.name,
                status="warn",
                message="OpenHands is configured but OPENHANDS_EXPERIMENTAL is false",
            )

        which_result = run(["which", config.openhands_command], check=False)
        if which_result.returncode != 0:
            return EngineDoctorResult(
                name=self.name,
                status="fail",
                message=f"OpenHands command not found: {config.openhands_command}",
            )

        probe = run([config.openhands_command, "--version"], check=False, timeout=10)
        if probe.returncode != 0:
            probe = run([config.openhands_command, "--help"], check=False, timeout=10)
        if probe.returncode != 0:
            detail = _summarize_output(probe.stderr or probe.stdout)
            return EngineDoctorResult(
                name=self.name,
                status="fail",
                message=detail or f"OpenHands command check failed: {config.openhands_command}",
            )

        return EngineDoctorResult(
            name=self.name,
            status="ok",
            message=f"OpenHands available via {config.openhands_command} (experimental)",
        )

    def _read_help_text(self) -> str:
        if self.command.endswith("run-openhands.sh"):
            return "--headless --task --file --json --override-with-envs -t -f"
        result = run([self.command, "--help"], check=False, timeout=10)
        if result.returncode != 0:
            return ""
        return f"{result.stdout}\n{result.stderr}"

    def _build_command(self, request: EngineRequest, help_text: str) -> list[str]:
        args = [self.command]
        if self._supports_flag(help_text, "--headless"):
            args.append("--headless")
        if self._supports_flag(help_text, "--override-with-envs"):
            args.append("--override-with-envs")
        args.extend(self.extra_args)

        if self.use_json_output and self._supports_flag(help_text, "--json"):
            args.append("--json")

        prompt_text = request.prompt_text or request.prompt_file.read_text()
        if prompt_text and self._supports_flag(help_text, "--task"):
            args.extend(["--task", prompt_text])
        elif prompt_text and self._supports_short_flag(help_text, "-t"):
            args.extend(["-t", prompt_text])
        elif self._supports_flag(help_text, "--file"):
            args.extend(["--file", str(request.prompt_file)])
        elif self._supports_short_flag(help_text, "-f"):
            args.extend(["-f", str(request.prompt_file)])
        else:
            # Fallback for CLIs that use `-t <prompt>` for a one-shot task.
            args.extend(["-t", prompt_text])
        return args

    def _supports_flag(self, help_text: str, flag: str) -> bool:
        return flag in help_text

    def _supports_short_flag(self, help_text: str, flag: str) -> bool:
        pattern = rf"(^|[\s,]){re.escape(flag)}([\s,]|$)"
        return re.search(pattern, help_text, flags=re.MULTILINE) is not None


def _summarize_output(output: str, max_length: int = 240) -> str:
    cleaned = _ANSI_RE.sub("", output or "")
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3] + "..."
