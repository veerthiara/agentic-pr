import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from typing import Optional

from agentic_pr.health import get_health_summary
from agentic_pr.config import AgentConfig


def _make_config(repo_path: Optional[Path] = None, **overrides):
    defaults = {
        "repo_path": repo_path or Path("/tmp/test-repo"),
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
        "log_dir": Path("/tmp/logs"),
        "run_dir": Path("/tmp/run"),
        "poll_interval_seconds": 300,
        "lock_file": Path("/tmp/agent.lock"),
        "run_record_dir": Path("/tmp/runs"),
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
        "comment_state_dir": Path("/tmp/comment-state"),
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
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


class HealthTests(unittest.TestCase):
    def test_check_config_ok(self) -> None:
        config = _make_config()
        check = get_health_summary(config)
        self.assertEqual(check.checks[0].name, "config")
        self.assertEqual(check.checks[0].status, "ok")

    def test_check_config_missing(self) -> None:
        config = _make_config(owner_repo="")
        check = get_health_summary(config)
        self.assertEqual(check.checks[0].status, "fail")

    @patch("agentic_pr.health.run")
    def test_check_gh_exists(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        config = _make_config()
        check = get_health_summary(config)
        gh = next((c for c in check.checks if c.name == "gh"), None)
        self.assertIsNotNone(gh)
        self.assertEqual(gh.status, "ok")

    @patch("agentic_pr.health.run")
    def test_check_gh_missing(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="command not found")
        config = _make_config()
        check = get_health_summary(config)
        gh = next((c for c in check.checks if c.name == "gh"), None)
        self.assertIsNotNone(gh)
        self.assertEqual(gh.status, "fail")

    @patch("agentic_pr.health.run")
    def test_check_ollama(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="qwen3-coder:30b", stderr="")
        config = _make_config()
        check = get_health_summary(config)
        ollama = next((c for c in check.checks if c.name == "ollama"), None)
        self.assertIsNotNone(ollama)
        self.assertEqual(ollama.status, "ok")

    @patch("agentic_pr.health.run")
    def test_check_ollama_fails(self, mock_run) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="could not connect")
        config = _make_config()
        check = get_health_summary(config)
        ollama = next((c for c in check.checks if c.name == "ollama"), None)
        self.assertIsNotNone(ollama)
        self.assertEqual(ollama.status, "fail")

    @patch("agentic_pr.health.run")
    def test_overall_status_ok(self, mock_run) -> None:
        """With a real temp repo dir, overall should not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config = _make_config(
                repo_path=repo, log_dir=repo / "logs", run_dir=repo / "run",
                lock_file=repo / "agent.lock", run_record_dir=repo / "runs",
                comment_state_dir=repo / "comment-state")
            import subprocess
            subprocess.run(["git", "init"], cwd=repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test"], cwd=repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=repo, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, capture_output=True)

            check = get_health_summary(config)
            self.assertIn(check.overall_status, ("ok", "warn", "fail"))

    def test_overall_status_fail_cfg(self) -> None:
        """Broken config gives overall fail."""
        config = _make_config(owner_repo="")
        check = get_health_summary(config)
        self.assertEqual(check.overall_status, "fail")