import tempfile
import unittest
from pathlib import Path

from agentic_pr.comment_state import CommentState, is_processed, load_comment_state, mark_processed
from agentic_pr.config import AgentConfig


class CommentStateTests(unittest.TestCase):
    def test_load_creates_empty_state_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            state = load_comment_state(config, 42)
            self.assertEqual(state.owner_repo, "octo/repo")
            self.assertEqual(state.pr_number, 42)
            self.assertEqual(state.processed_comment_ids, [])

    def test_mark_processed_writes_and_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            mark_processed(config, 42, "comment-1")
            mark_processed(config, 42, "comment-2")
            state = load_comment_state(config, 42)
            self.assertEqual(state.processed_comment_ids, ["comment-1", "comment-2"])

    def test_is_processed_returns_true_after_mark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            self.assertFalse(is_processed(config, 42, "comment-1"))
            mark_processed(config, 42, "comment-1")
            self.assertTrue(is_processed(config, 42, "comment-1"))

    def test_is_processed_returns_false_for_different_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            mark_processed(config, 42, "comment-1")
            self.assertFalse(is_processed(config, 42, "comment-2"))

    def test_state_is_per_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            mark_processed(config, 42, "comment-1")
            self.assertFalse(is_processed(config, 43, "comment-1"))


def _config(root: Path) -> AgentConfig:
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
        pr_followup_require_label=False,
        label_followup="agent-followup",
        label_followup_running="agent-followup-running",
        label_followup_done="agent-followup-done",
        label_followup_failed="agent-followup-failed",
        comment_state_dir=root / "comment-state",
        max_followup_comments_per_cycle=1,
    )