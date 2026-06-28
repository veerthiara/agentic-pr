import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_pr.config import AgentConfig
from agentic_pr.engines.base import EngineRequest
from agentic_pr.engines.openhands_engine import OpenHandsEngine


def _make_config(**overrides) -> AgentConfig:
    root = Path(tempfile.mkdtemp())
    defaults = {
        "repo_path": root / "repo",
        "owner_repo": "test/repo",
        "base_branch": "main",
        "model": "ollama/qwen3-coder:30b",
        "label_todo": "agent-run",
        "label_running": "agent-running",
        "label_done": "agent-pr-created",
        "label_failed": "agent-failed",
        "label_no_changes": "agent-no-changes",
        "label_blocked": "agent-blocked",
        "ollama_api_base": "http://localhost:11434",
        "aider_extra_args": (),
        "log_dir": root / "logs",
        "run_dir": root / "run",
        "poll_interval_seconds": 300,
        "lock_file": root / "agent.lock",
        "run_record_dir": root / "runs",
        "agent_host_label": "Mac Studio",
        "comment_on_start": True,
        "comment_on_success": True,
        "comment_on_failure": True,
        "comment_on_no_changes": True,
        "aider_timeout_seconds": 1800,
        "max_changed_files": 20,
        "max_diff_lines": 800,
        "require_aiderignore": True,
        "blocked_path_patterns": (".env",),
        "test_cmd": "",
        "lint_cmd": "",
        "stale_lock_seconds": 7200,
        "enable_planner": True,
        "planner_model": "ollama/qwen3-coder:30b",
        "repo_context_max_files": 80,
        "repo_context_max_bytes": 120000,
        "planner_timeout_seconds": 900,
        "comment_plan": True,
        "enable_pr_followups": True,
        "pr_followup_command_prefix": "/agent",
        "pr_followup_require_label": False,
        "label_followup": "agent-followup",
        "label_followup_running": "agent-followup-running",
        "label_followup_done": "agent-followup-done",
        "label_followup_failed": "agent-followup-failed",
        "comment_state_dir": root / "comment-state",
        "max_followup_comments_per_cycle": 1,
        "enable_ci_context": True,
        "ci_command_aliases": ("/agent fix-ci", "/agent fix checks", "/agent fix failing tests"),
        "ci_log_max_lines": 250,
        "ci_log_max_bytes": 40000,
        "ci_include_successful_checks": False,
        "ci_require_failed_checks": False,
        "enable_repo_instructions": True,
        "repo_instructions_dir": ".agentic-pr",
        "repo_instructions_max_bytes": 40000,
        "run_retention_days": 30,
        "log_retention_days": 30,
        "prompt_retention_days": 30,
        "comment_state_retention_days": 90,
        "max_log_preview_lines": 80,
        "service_label": None,
        "engine": "openhands",
        "engine_timeout_seconds": 3600,
        "openhands_command": "openhands",
        "openhands_timeout_seconds": 3600,
        "openhands_extra_args": (),
        "openhands_use_json_output": False,
        "openhands_experimental": True,
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


class OpenHandsEngineTests(unittest.TestCase):
    def test_build_command_prefers_prompt_file_when_supported(self) -> None:
        engine = OpenHandsEngine(command="openhands", extra_args=("--workspace-write",), use_json_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            request = EngineRequest(
                run_id="run-1",
                repo_path=Path(tmp),
                prompt_file=Path(tmp) / "prompt.md",
                prompt_text="fix calc.py",
                model="ignored",
                log_file=Path(tmp) / "run.log",
                timeout_seconds=3600,
            )
            command = engine._build_command(request, "Usage: openhands --headless --json --file FILE --task PROMPT --override-with-envs")

        self.assertEqual(
            command,
            ["openhands", "--headless", "--override-with-envs", "--workspace-write", "--json", "--task", "fix calc.py"],
        )

    def test_build_command_falls_back_to_task_text(self) -> None:
        engine = OpenHandsEngine(command="openhands")
        with tempfile.TemporaryDirectory() as tmp:
            request = EngineRequest(
                run_id="run-1",
                repo_path=Path(tmp),
                prompt_file=Path(tmp) / "prompt.md",
                prompt_text="fix calc.py",
                timeout_seconds=3600,
            )
            command = engine._build_command(request, "Usage: openhands --headless --task PROMPT --override-with-envs")

        self.assertEqual(command, ["openhands", "--headless", "--override-with-envs", "--task", "fix calc.py"])

    @patch("agentic_pr.engines.openhands_engine.run")
    def test_run_respects_timeout_value(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="help", stderr="", timed_out=False),
            MagicMock(returncode=124, stdout="", stderr="", timed_out=True),
        ]
        engine = OpenHandsEngine(command="openhands")
        with tempfile.TemporaryDirectory() as tmp:
            request = EngineRequest(
                run_id="run-1",
                repo_path=Path(tmp),
                prompt_file=Path(tmp) / "prompt.md",
                prompt_text="fix calc.py",
                log_file=Path(tmp) / "run.log",
                timeout_seconds=45,
            )
            result = engine.run(request)

        run_call = mock_run.call_args_list[1]
        self.assertEqual(run_call.kwargs["timeout"], 45)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.error_summary, "OpenHands timed out after 45 seconds")

    @patch("agentic_pr.engines.openhands_engine.run")
    def test_doctor_reports_missing_command(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found", timed_out=False)
        result = OpenHandsEngine().doctor(_make_config())
        self.assertEqual(result.status, "fail")
        self.assertIn("OpenHands command not found", result.message)

    @patch("agentic_pr.engines.openhands_engine.run")
    def test_doctor_reports_available_command(self, mock_run) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/usr/local/bin/openhands", stderr="", timed_out=False),
            MagicMock(returncode=0, stdout="OpenHands 1.0", stderr="", timed_out=False),
        ]
        result = OpenHandsEngine().doctor(_make_config())
        self.assertEqual(result.status, "ok")
        self.assertIn("experimental", result.message)
