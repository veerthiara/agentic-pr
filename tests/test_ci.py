from __future__ import annotations

import json
import unittest
from unittest.mock import patch, MagicMock

from agentic_pr.ci import CheckResult, get_pr_checks, get_failing_checks, has_failing_checks, get_workflow_run_logs, _truncate_logs
from agentic_pr.config import AgentConfig
from pathlib import Path


class CITests(unittest.TestCase):
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
        )

    @patch("agentic_pr.ci.run")
    def test_get_pr_checks_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"name": "test", "state": "completed", "conclusion": "success", "detailsUrl": "https://example.com/1", "workflowRunId": 123, "checkRunId": 456},
            {"name": "lint", "state": "completed", "conclusion": "failure", "detailsUrl": "https://example.com/2", "workflowRunId": 124, "checkRunId": 457},
        ])
        mock_run.return_value = mock_result

        config = self._config()
        checks = get_pr_checks(config, 15)

        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0].name, "test")
        self.assertEqual(checks[0].conclusion, "success")
        self.assertEqual(checks[1].name, "lint")
        self.assertEqual(checks[1].conclusion, "failure")

    @patch("agentic_pr.ci.run")
    def test_get_pr_checks_no_checks(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "no checks found"
        mock_run.return_value = mock_result

        config = self._config()
        checks = get_pr_checks(config, 15)

        self.assertEqual(checks, [])

    @patch("agentic_pr.ci.run")
    def test_get_pr_checks_invalid_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        config = self._config()
        checks = get_pr_checks(config, 15)

        self.assertEqual(checks, [])

    @patch("agentic_pr.ci.get_pr_checks")
    def test_get_failing_checks(self, mock_get_checks):
        mock_get_checks.return_value = [
            CheckResult(name="test", state="completed", conclusion="success", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
            CheckResult(name="lint", state="completed", conclusion="failure", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
            CheckResult(name="build", state="completed", conclusion="action_required", details_url=None, workflow_run_id=None, check_run_id=None, raw={}),
        ]

        config = self._config()
        failing = get_failing_checks(config, 15)

        self.assertEqual(len(failing), 2)
        self.assertEqual(failing[0].name, "lint")
        self.assertEqual(failing[1].name, "build")

    @patch("agentic_pr.ci.get_failing_checks")
    def test_has_failing_checks_true(self, mock_get_failing):
        mock_get_failing.return_value = [CheckResult(name="lint", state="completed", conclusion="failure", details_url=None, workflow_run_id=None, check_run_id=None, raw={})]

        config = self._config()
        result = has_failing_checks(config, 15)

        self.assertTrue(result)

    @patch("agentic_pr.ci.get_failing_checks")
    def test_has_failing_checks_false(self, mock_get_failing):
        mock_get_failing.return_value = []

        config = self._config()
        result = has_failing_checks(config, 15)

        self.assertFalse(result)

    def test_truncate_logs_by_lines(self):
        logs = "\n".join([f"line {i}" for i in range(300)])
        result = _truncate_logs(logs, max_lines=100, max_bytes=100000)
        lines = result.splitlines()
        self.assertEqual(len(lines), 101)  # 100 lines + truncation message
        self.assertTrue(result.endswith("[truncated]"))

    def test_truncate_logs_by_bytes(self):
        logs = "x" * 50000
        result = _truncate_logs(logs, max_lines=1000, max_bytes=1000)
        self.assertLessEqual(len(result.encode("utf-8")), 1000 + 20)  # + truncation message
        self.assertTrue(result.endswith("[truncated]"))

    def test_truncate_logs_no_truncation(self):
        logs = "short log"
        result = _truncate_logs(logs, max_lines=100, max_bytes=10000)
        self.assertEqual(result, "short log")

    @patch("agentic_pr.ci.run")
    def test_get_workflow_run_logs_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Error: test failed\n  at test_file.py:10"
        mock_run.return_value = mock_result

        config = self._config()
        logs = get_workflow_run_logs(config, 123, max_lines=10, max_bytes=1000)

        self.assertIn("Error: test failed", logs)

    @patch("agentic_pr.ci.run")
    def test_get_workflow_run_logs_failure(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "run not found"
        mock_run.return_value = mock_result

        config = self._config()
        logs = get_workflow_run_logs(config, 123)

        self.assertIn("Failed to fetch logs", logs)


if __name__ == "__main__":
    unittest.main()