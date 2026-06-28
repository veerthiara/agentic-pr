import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_pr.config import AgentConfig
from agentic_pr.engine import get_engine, list_supported_engines
from agentic_pr.engines.aider_engine import AiderEngine
from agentic_pr.engines.base import EngineRequest
from agentic_pr.engines.openhands_engine import OpenHandsEngine


def _make_config(**overrides) -> AgentConfig:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
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
        "engine": "aider",
        "engine_timeout_seconds": 1800,
        "openhands_command": "openhands",
        "openhands_timeout_seconds": 3600,
        "openhands_extra_args": (),
        "openhands_use_json_output": False,
        "openhands_experimental": False,
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


class EngineTests(unittest.TestCase):
    def test_list_supported_engines(self) -> None:
        self.assertEqual(list_supported_engines(), ["aider", "openhands"])

    def test_get_engine_returns_aider_engine(self) -> None:
        engine = get_engine(_make_config(engine="aider"))
        self.assertIsInstance(engine, AiderEngine)
        self.assertEqual(engine.name, "aider")

    def test_get_engine_returns_openhands_engine(self) -> None:
        engine = get_engine(
            _make_config(
                engine="openhands",
                openhands_experimental=True,
                openhands_extra_args=("--workspace-write",),
            )
        )
        self.assertIsInstance(engine, OpenHandsEngine)
        self.assertEqual(engine.command, "openhands")
        self.assertEqual(engine.extra_args, ("--workspace-write",))

    def test_get_engine_requires_openhands_experimental_flag(self) -> None:
        with self.assertRaisesRegex(Exception, "OPENHANDS_EXPERIMENTAL=true"):
            get_engine(_make_config(engine="openhands", openhands_experimental=False))

    def test_get_engine_rejects_unknown_engine(self) -> None:
        with self.assertRaisesRegex(Exception, "Supported engines: aider, openhands"):
            get_engine(_make_config(engine="unknown"))


class AiderEngineTests(unittest.TestCase):
    @patch("agentic_pr.engines.aider_engine.run")
    def test_aider_engine_run_success(self, mock_run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = AiderEngine()
            request = EngineRequest(
                run_id="test-123",
                repo_path=Path(tmp),
                prompt_file=Path(tmp) / "prompt.md",
                prompt_text="Test prompt",
                model="ollama/qwen3-coder:30b",
                log_file=Path(tmp) / "test.log",
                timeout_seconds=1800,
                mode="issue",
            )

            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="", timed_out=False)

            result = engine.run(request)

            self.assertTrue(result.ok)
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(result.timed_out)
            self.assertEqual(result.engine_name, "aider")
            self.assertIsNotNone(result.log_file)

    @patch("agentic_pr.engines.aider_engine.run")
    def test_aider_engine_run_timeout(self, mock_run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = AiderEngine()
            request = EngineRequest(
                run_id="test-123",
                repo_path=Path(tmp),
                prompt_file=Path(tmp) / "prompt.md",
                prompt_text="Test prompt",
                model="ollama/qwen3-coder:30b",
                log_file=Path(tmp) / "test.log",
                timeout_seconds=1800,
                mode="issue",
            )

            mock_run.return_value = MagicMock(returncode=124, stdout="Partial output", stderr="", timed_out=True)

            result = engine.run(request)

            self.assertFalse(result.ok)
            self.assertTrue(result.timed_out)
            self.assertEqual(result.error_summary, "Aider timed out after 1800 seconds")

    @patch("agentic_pr.engines.aider_engine.run")
    def test_aider_engine_doctor(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="/usr/local/bin/aider", stderr="")
        result = AiderEngine().doctor(_make_config())
        self.assertEqual(result.name, "aider")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "aider available")

    @patch("agentic_pr.engines.aider_engine.run")
    def test_aider_engine_doctor_not_found(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="command not found")
        result = AiderEngine().doctor(_make_config())
        self.assertEqual(result.name, "aider")
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.message, "aider command not found")
