from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_pr.command import run
from agentic_pr.config import AgentConfig
from agentic_pr.engines.base import CodingEngine, EngineRequest, EngineResult, EngineDoctorResult


class AiderEngine(CodingEngine):
    """Aider coding engine implementation."""

    @property
    def name(self) -> str:
        return "aider"

    def run(self, request: EngineRequest) -> EngineResult:
        """Run Aider with the given request."""
        import time
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Ensure directories exist
        request.repo_path.mkdir(parents=True, exist_ok=True)
        if request.log_file:
            request.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write prompt file
        request.prompt_file.write_text(request.prompt_text or "")
        
        # Build Aider command
        args = [
            "aider",
            "--model",
            request.model,
            "--no-auto-commits",
            "--no-dirty-commits",
            "--yes-always",
            "--message-file",
            str(request.prompt_file),
        ]
        
        # Run Aider
        result = run(
            args,
            cwd=request.repo_path,
            check=False,
            timeout=request.timeout_seconds,
            env=request.env
        )
        
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Write log file
        log_content = result.stdout + result.stderr
        if result.timed_out:
            log_content += f"\nAider timed out after {request.timeout_seconds} seconds.\n"
        
        if request.log_file:
            request.log_file.write_text(log_content)
        
        # Determine error summary
        error_summary = None
        if result.timed_out:
            error_summary = f"Aider timed out after {request.timeout_seconds} seconds"
        elif result.returncode != 0:
            error_summary = f"Aider exited with code {result.returncode}"
        
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
        """Check Aider availability."""
        try:
            result = run(["which", "aider"], check=False)
            if result.returncode != 0:
                return EngineDoctorResult(
                    name=self.name,
                    status="fail",
                    message="aider command not found"
                )
            return EngineDoctorResult(
                name=self.name,
                status="ok",
                message="aider available"
            )
        except Exception as exc:
            return EngineDoctorResult(
                name=self.name,
                status="fail",
                message=f"aider check failed: {exc}"
            )