import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_pr.config import AgentConfig
from agentic_pr.safety import check_safety, path_is_blocked


class SafetyTests(unittest.TestCase):
    def test_blocked_paths_are_detected(self) -> None:
        patterns = (".env", ".env.*", "*.pem", "secrets/*")
        self.assertTrue(path_is_blocked(".env", patterns))
        self.assertTrue(path_is_blocked("secrets/token.txt", patterns))
        self.assertFalse(path_is_blocked("src/app.py", patterns))

    def test_changed_files_limit_blocks(self) -> None:
        config = _config(max_changed_files=1)
        with patch("agentic_pr.safety.changed_files", return_value=["src/a.py", "src/b.py"]), patch("agentic_pr.safety.diff_line_count", return_value=2):
            result = check_safety(config)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "too_many_files")

    def test_diff_line_limit_blocks(self) -> None:
        config = _config(max_diff_lines=10)
        with patch("agentic_pr.safety.changed_files", return_value=["src/a.py"]), patch("agentic_pr.safety.diff_line_count", return_value=11):
            result = check_safety(config)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "diff_too_large")


def _config(max_changed_files: int = 20, max_diff_lines: int = 800) -> AgentConfig:
    root = Path("/tmp/agentic-pr-tests")
    return AgentConfig(
        repo_path=root / "repo", owner_repo="octo/repo", base_branch="main", model="ollama/qwen3-coder:30b",
        label_todo="agent-run", label_running="agent-running", label_done="agent-pr-created", label_failed="agent-failed", label_no_changes="agent-no-changes", label_blocked="agent-blocked",
        ollama_api_base="http://localhost:11434", aider_extra_args=(), log_dir=root / "logs", run_dir=root / "run", poll_interval_seconds=300, lock_file=root / "run" / "agent.lock", run_record_dir=root / "runs",
        agent_host_label="Mac Studio", comment_on_start=True, comment_on_success=True, comment_on_failure=True, comment_on_no_changes=True,
        aider_timeout_seconds=1800, max_changed_files=max_changed_files, max_diff_lines=max_diff_lines, require_aiderignore=True, blocked_path_patterns=(".env", ".env.*", "*.pem", "*.key", "secrets/*"), test_cmd="", lint_cmd="", stale_lock_seconds=7200,
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
