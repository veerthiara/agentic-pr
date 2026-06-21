import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_pr.command import CommandResult
from agentic_pr.config import AgentConfig
from agentic_pr.github_ops import Issue
from agentic_pr.planner import ollama_cli_model, run_planner
from agentic_pr.repo_context import RepoContext
from agentic_pr.repo_instructions import RepoInstructions


class PlannerTests(unittest.TestCase):
    def test_ollama_cli_model_strips_aider_prefix(self) -> None:
        self.assertEqual(ollama_cli_model("ollama/qwen3-coder:30b"), "qwen3-coder:30b")
        self.assertEqual(ollama_cli_model("qwen3-coder:30b"), "qwen3-coder:30b")

    def test_planner_timeout_falls_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            issue = Issue(1, "Title", "Body", "now")
            context = RepoContext(Path(tmp), "main", [], [], [], {}, [])
            with patch("agentic_pr.planner.run", return_value=CommandResult(["ollama"], 124, "partial", "", True)):
                result = run_planner(config, issue, context, "run-1")

            self.assertFalse(result.ok)
            self.assertEqual(result.status, "timeout")
            self.assertTrue(result.output_file.exists())

    def test_planner_parses_basic_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            issue = Issue(1, "Title", "Body", "now")
            context = RepoContext(Path(tmp), "main", [], [], [], {}, [])
            output = """Summary\nBuild FastAPI app.\nFiles likely to modify\n- README.md\nFiles likely to create\n- main.py\nTest plan\nRun pytest.\n"""
            with patch("agentic_pr.planner.run", return_value=CommandResult(["ollama"], 0, output, "", False)):
                result = run_planner(config, issue, context, "run-1")

            self.assertTrue(result.ok)
            self.assertEqual(result.summary, "Build FastAPI app.")
            self.assertEqual(result.files_to_modify, ["README.md"])
            self.assertEqual(result.files_to_create, ["main.py"])

    def test_planner_failure_error_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            issue = Issue(1, "Title", "Body", "now")
            context = RepoContext(Path(tmp), "main", [], [], [], {}, [])
            noisy = "\x1b[?2026h\x1b[1Gpulling manifest ⠋ \x1b[K\x1b[?2026l\nError: pull model manifest: file does not exist"
            with patch("agentic_pr.planner.run", return_value=CommandResult(["ollama"], 1, "", noisy, False)):
                result = run_planner(config, issue, context, "run-2")

            self.assertFalse(result.ok)
            self.assertNotIn("\x1b", result.error or "")
            self.assertIn("file does not exist", result.error or "")

    def test_planner_includes_repo_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            issue = Issue(1, "Title", "Body", "now")
            context = RepoContext(Path(tmp), "main", [], [], [], {}, [])
            instructions = RepoInstructions(
                instructions_text="Test instructions",
                safety_text="Test safety",
                examples_text="Test examples"
            )
            output = "Summary\nDid a thing.\n"
            with patch("agentic_pr.planner.run", return_value=CommandResult(["ollama"], 0, output, "", False)) as mock_run:
                run_planner(config, issue, context, "run-1", repo_instructions=instructions)
                
            input_text = mock_run.call_args.kwargs["input_text"]
            self.assertIn("Project Instructions:\nTest instructions", input_text)
            self.assertIn("Safety Rules:\nTest safety", input_text)
            self.assertIn("Examples:\nTest examples", input_text)


def _config(root: Path) -> AgentConfig:
    return AgentConfig(
        repo_path=root / "repo", owner_repo="octo/repo", base_branch="main", model="ollama/qwen3-coder:30b",
        label_todo="agent-run", label_running="agent-running", label_done="agent-pr-created", label_failed="agent-failed", label_no_changes="agent-no-changes", label_blocked="agent-blocked",
        ollama_api_base="http://localhost:11434", aider_extra_args=(), log_dir=root / "logs", run_dir=root / "run", poll_interval_seconds=60, lock_file=root / "run" / "agent.lock", run_record_dir=root / "runs",
        agent_host_label="Mac Studio", comment_on_start=True, comment_on_success=True, comment_on_failure=True, comment_on_no_changes=True,
        aider_timeout_seconds=1800, max_changed_files=20, max_diff_lines=800, require_aiderignore=True, blocked_path_patterns=(".env",), test_cmd="", lint_cmd="", stale_lock_seconds=7200,
        enable_planner=True, planner_model="ollama/qwen3-coder:30b", repo_context_max_files=80, repo_context_max_bytes=120000, planner_timeout_seconds=900, comment_plan=True,
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
