from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from agentic_pr.ci_context import CIContext, build_ci_context
from agentic_pr.config import AgentConfig
from pathlib import Path


class CIContextTests(unittest.TestCase):
    def _config(self) -> AgentConfig:
        root = Path("/tmp/agentic-pr-tests")
        return AgentConfig(
            repo_path=root / "repo",
            owner_repo="octo/repo",
            base_branch="main",
            model="ollama/qwen3-coder:30b",
            label_todo="agent-run",
            label_running="agent-running",
            label_done="agent-pr-created",
            label_failed="agent-failed",
            label_no_changes="agent-no-changes",
            label_blocked="agent-blocked",
            ollama_api_base="http://localhost:11434",
            aider_extra_args=(),
            log_dir=root / "logs",
            run_dir=root / "run",
            poll_interval_seconds=300,
            lock_file=root / "run" / "agent.lock",
            run_record_dir=root / "runs",
            agent_host_label="Mac Studio",
            comment_on_start=True,
            comment_on_success=True,
            comment_on_failure=True,
            comment_on_no_changes=True,
            aider_timeout_seconds=1800,
            max_changed_files=20,
            max_diff_lines=800,
            require_aiderignore=True,
            blocked_path_patterns=(".env",),
            test_cmd="",
            lint_cmd="",
            stale_lock_seconds=7200,
            enable_planner=True,
            planner_model="ollama/qwen3-coder:30b",
            repo_context_max_files=80,
            repo_context_max_bytes=120000,
            planner_timeout_seconds=900,
            comment_plan=True,
            enable_pr_followups=True,
            pr_followup_command_prefix="/agent",
            pr_followup_require_label=False,
            label_followup="agent-followup",
            label_followup_running="agent-followup-running",
            label_followup_done="agent-followup-done",
            label_followup_failed="agent-followup-failed",
            comment_state_dir=root / "comment-state",
            max_followup_comments_per_cycle=1,
            enable_ci_context=True,
            ci_command_aliases=("/agent fix-ci", "/agent fix checks", "/agent fix failing tests"),
            ci_log_max_lines=250,
            ci_log_max_bytes=40000,
            ci_include_successful_checks=False,
            ci_require_failed_checks=False,
            enable_repo_instructions=True,
            repo_instructions_dir=".agentic-pr",
            repo_instructions_max_bytes=40000,
        )

    @patch("agentic_pr.ci_context.get_pr_checks")
    def test_build_ci_context_no_checks(self, mock_get_checks):
        mock_get_checks.return_value = []

        config = self._config()
        context = build_ci_context(config, 15)

        self.assertFalse(context.checks_found)
        self.assertFalse(context.failing_checks_found)
        self.assertEqual(context.failed_check_names, [])
        self.assertEqual(context.log_excerpt, "")
        self.assertIn("No checks found", context.warnings[0])

    @patch("agentic_pr.ci_context.get_pr_checks")
    @patch("agentic_pr.ci_context.get_failing_checks")
    def test_build_ci_context_all_passing(self, mock_get_failing, mock_get_checks):
        mock_get_checks.return_value = [
            MagicMock(name="test", state="completed", conclusion="success", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
            MagicMock(name="lint", state="completed", conclusion="success", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
        ]
        mock_get_failing.return_value = []

        config = self._config()
        context = build_ci_context(config, 15)

        self.assertTrue(context.checks_found)
        self.assertFalse(context.failing_checks_found)
        self.assertEqual(context.failed_check_names, [])
        self.assertEqual(context.log_excerpt, "")

    @patch("agentic_pr.ci_context.get_pr_checks")
    @patch("agentic_pr.ci_context.get_failing_checks")
    @patch("agentic_pr.ci_context.get_workflow_run_logs")
    def test_build_ci_context_with_failing_checks(self, mock_get_logs, mock_get_failing, mock_get_checks):
        from agentic_pr.ci import CheckResult
        mock_get_checks.return_value = [
            CheckResult(name="test", state="completed", conclusion="success", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
            CheckResult(name="lint", state="completed", conclusion="failure", details_url=None, workflow_run_id=123, check_run_id=None, raw={}),
        ]
        mock_get_failing.return_value = [
            CheckResult(name="lint", state="completed", conclusion="failure", details_url=None, workflow_run_id=123, check_run_id=None, raw={}),
        ]
        mock_get_logs.return_value = "Error: lint failed\n  at file.py:10"

        config = self._config()
        context = build_ci_context(config, 15)

        self.assertTrue(context.checks_found)
        self.assertTrue(context.failing_checks_found)
        self.assertEqual(context.failed_check_names, ["lint"])
        self.assertIn("lint failed", context.log_excerpt)

    @patch("agentic_pr.ci_context.get_pr_checks")
    @patch("agentic_pr.ci_context.get_failing_checks")
    def test_build_ci_context_require_failed_checks_true(self, mock_get_failing, mock_get_checks):
        mock_get_checks.return_value = [
            MagicMock(name="test", state="completed", conclusion="success", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
        ]
        mock_get_failing.return_value = []

        config = self._config()
        # Create a new config with ci_require_failed_checks=True
        from dataclasses import replace
        config = replace(config, ci_require_failed_checks=True)
        context = build_ci_context(config, 15)

        self.assertTrue(context.checks_found)
        self.assertFalse(context.failing_checks_found)
        self.assertIn("CI_REQUIRE_FAILED_CHECKS=true but no failing checks found", context.warnings[0])

    def test_ci_context_truncation_by_lines(self):
        # Test that long logs are truncated by lines
        from dataclasses import replace
        config = replace(self._config(), ci_log_max_lines=5, ci_log_max_bytes=100000)
        
        # We can't easily test this without mocking, but we can verify the logic
        # by checking the _truncate_logs function directly
        from agentic_pr.ci import _truncate_logs
        logs = "\n".join([f"line {i}" for i in range(100)])
        result = _truncate_logs(logs, max_lines=5, max_bytes=100000)
        lines = result.splitlines()
        self.assertEqual(len(lines), 6)  # 5 lines + truncation message

    def test_ci_context_truncation_by_bytes(self):
        from dataclasses import replace
        config = replace(self._config(), ci_log_max_lines=1000, ci_log_max_bytes=100)
        
        from agentic_pr.ci import _truncate_logs
        logs = "x" * 500
        result = _truncate_logs(logs, max_lines=1000, max_bytes=100)
        self.assertLessEqual(len(result.encode("utf-8")), 120)  # + truncation message


if __name__ == "__main__":
    unittest.main()