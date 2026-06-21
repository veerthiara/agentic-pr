import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_pr.command import CommandResult
from agentic_pr.config import AgentConfig
from agentic_pr.pr_followup import FollowupTask, find_pending_followup


class PrFollowupTests(unittest.TestCase):
    def test_followup_command_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{
                "number": 5,
                "title": "Test PR",
                "headRefName": "agent/issue-5-123",
                "baseRefName": "main",
                "labels": [],
                "url": "https://github.com/octo/repo/pull/5",
            }]
            details = {
                "comments": [
                    {"id": "c1", "body": "/agent fix the tests", "author": {"login": "user1"}},
                ],
                "headRefName": "agent/issue-5-123",
                "baseRefName": "main",
                "title": "Test PR",
                "url": "https://github.com/octo/repo/pull/5",
            }
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertEqual(task.pr_number, 5)
            self.assertEqual(task.command_text, "fix the tests")
            self.assertEqual(task.comment_author, "user1")

    def test_comment_without_prefix_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "just a comment", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNone(task)

    def test_processed_comment_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            from agentic_pr.comment_state import mark_processed
            mark_processed(config, 5, "c1")
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent do something", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNone(task)

    def test_bot_comment_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent do something", "author": {"login": "github-actions[bot]"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNone(task)

    def test_require_label_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp), pr_followup_require_label=True)
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [{"name": "other"}], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent do something", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNone(task)

    def test_only_one_followup_per_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [
                {"number": 5, "title": "PR 1", "headRefName": "b1", "baseRefName": "main", "labels": [], "url": ""},
                {"number": 6, "title": "PR 2", "headRefName": "b2", "baseRefName": "main", "labels": [], "url": ""},
            ]
            details1 = {"comments": [{"id": "c1", "body": "/agent first", "author": {"login": "user1"}}], "headRefName": "b1", "baseRefName": "main", "title": "PR 1", "url": ""}
            details2 = {"comments": [{"id": "c2", "body": "/agent second", "author": {"login": "user1"}}], "headRefName": "b2", "baseRefName": "main", "title": "PR 2", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details1), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertEqual(task.pr_number, 5)

    def test_ci_fix_ci_command_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent fix-ci", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertTrue(task.is_ci_fix)
            self.assertEqual(task.ci_command_alias, "/agent fix-ci")

    def test_ci_fix_checks_command_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent fix checks", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertTrue(task.is_ci_fix)
            self.assertEqual(task.ci_command_alias, "/agent fix checks")

    def test_ci_fix_failing_tests_command_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent fix failing tests", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertTrue(task.is_ci_fix)
            self.assertEqual(task.ci_command_alias, "/agent fix failing tests")

    def test_generic_agent_command_not_ci_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            prs = [{"number": 5, "title": "Test PR", "headRefName": "b", "baseRefName": "main", "labels": [], "url": ""}]
            details = {"comments": [{"id": "c1", "body": "/agent update README", "author": {"login": "user1"}}], "headRefName": "b", "baseRefName": "main", "title": "Test PR", "url": ""}
            with patch("agentic_pr.pr_followup.run") as mock_run:
                mock_run.side_effect = [
                    CommandResult(["gh"], 0, json_dumps(prs), "", False),
                    CommandResult(["gh"], 0, json_dumps(details), "", False),
                ]
                task = find_pending_followup(config)

            self.assertIsNotNone(task)
            self.assertFalse(task.is_ci_fix)
            self.assertIsNone(task.ci_command_alias)


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj)


def _config(root: Path, pr_followup_require_label: bool = False) -> AgentConfig:
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
        poll_interval_seconds=60,
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
        pr_followup_require_label=pr_followup_require_label,
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