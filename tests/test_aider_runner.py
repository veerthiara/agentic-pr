import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_pr.command import CommandResult
from agentic_pr.config import AgentConfig

from agentic_pr.aider_runner import build_prompt
from agentic_pr.github_ops import Issue


class AiderRunnerTests(unittest.TestCase):
    def test_prompt_generation(self) -> None:
        prompt = build_prompt(Issue(number=9, title="Fix docs", body="Please update README", created_at="2026-01-01"))

        self.assertIn("GitHub issue: #9", prompt)
        self.assertIn("Title: Fix docs", prompt)
        self.assertIn("Please update README", prompt)


    def test_timeout_result_is_returned(self) -> None:
        from agentic_pr.aider_runner import run_aider

        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            issue = Issue(number=9, title="Fix docs", body="Body", created_at="2026-01-01")
            with patch("agentic_pr.aider_runner.run", return_value=CommandResult(["aider"], 124, "", "timeout", True)):
                result = run_aider(config, issue, "run-1")

            self.assertTrue(result.timed_out)
            self.assertIn("timed out", result.log_file.read_text())


def _config(root: Path) -> AgentConfig:
    return AgentConfig(
        repo_path=root / "repo", owner_repo="octo/repo", base_branch="main", model="ollama/qwen3-coder:30b",
        label_todo="agent-run", label_running="agent-running", label_done="agent-pr-created", label_failed="agent-failed", label_no_changes="agent-no-changes", label_blocked="agent-blocked",
        ollama_api_base="http://localhost:11434", aider_extra_args=(), log_dir=root / "logs", run_dir=root / "run", poll_interval_seconds=300, lock_file=root / "run" / "agent.lock", run_record_dir=root / "runs",
        agent_host_label="Mac Studio", comment_on_start=True, comment_on_success=True, comment_on_failure=True, comment_on_no_changes=True,
        aider_timeout_seconds=1, max_changed_files=20, max_diff_lines=800, require_aiderignore=True, blocked_path_patterns=(".env",), test_cmd="", lint_cmd="", stale_lock_seconds=7200,
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
