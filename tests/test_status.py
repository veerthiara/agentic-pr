from datetime import datetime
import unittest

from agentic_pr.config import AgentConfig
from agentic_pr.github_ops import Issue
from agentic_pr.status import (
    before_aider_comment,
    failed_comment,
    generate_run_id,
    no_changes_comment,
    pr_body,
    pr_created_comment,
    start_comment,
    status_labels,
    blocked_comment,
    preflight_blocked_comment,
    aider_timeout_comment,
    validation_failed_comment,
    planner_started_comment,
    planner_completed_comment,
    planner_failed_comment,
    implementation_started_comment,
)


class StatusTests(unittest.TestCase):
    def test_run_id_generation(self) -> None:
        run_id = generate_run_id(42, datetime(2026, 6, 19, 15, 4, 5))
        self.assertEqual(run_id, "run-20260619-150405-issue-42")

    def test_status_label_list(self) -> None:
        self.assertEqual(
            status_labels(_config()),
            ["agent-run", "agent-running", "agent-pr-created", "agent-failed", "agent-no-changes", "agent-blocked"],
        )

    def test_issue_comment_text_generation(self) -> None:
        config = _config()
        self.assertIn("Local Mac Studio agent started", start_comment(config, "run-1"))
        self.assertIn("Running Aider", before_aider_comment(config, "run-1"))
        self.assertIn("https://example.test/pr/1", pr_created_comment("run-1", "https://example.test/pr/1", "agent/branch"))
        self.assertIn("no file changes", no_changes_comment("run-1"))
        self.assertIn("Stage: `run_aider`", failed_comment("run-1", "run_aider", "boom"))
        self.assertIn("run-1", blocked_comment("run-1", "blocked_path", ["Blocked path: .env"]))
        self.assertIn("missing_aiderignore", preflight_blocked_comment("run-1", "missing_aiderignore", ["missing"]))
        self.assertIn("1800", aider_timeout_comment("run-1", 1800))
        self.assertIn("lint", validation_failed_comment("run-1", "lint", "failed"))
        self.assertIn("run-1", planner_started_comment("run-1"))
        self.assertIn("summary", planner_completed_comment("run-1", "summary"))
        self.assertIn("continue", planner_failed_comment("run-1", "timeout"))
        self.assertIn("run-1", implementation_started_comment("run-1"))

    def test_pr_body_generation(self) -> None:
        config = _config()
        issue = Issue(number=7, title="Add min", body="body", created_at="2026-01-01")
        body = pr_body(
            config=config,
            issue=issue,
            run_id="run-20260619-150405-issue-7",
            branch="agent/issue-7-20260619150405",
            log_file="/tmp/run.log",
            aider_exit_code=0,
        )

        self.assertIn("Closes #7", body)
        self.assertIn("run-20260619-150405-issue-7", body)
        self.assertIn("ollama/qwen3-coder:30b", body)
        self.assertIn("Agent host: `Mac Studio`", body)
        self.assertIn("not auto-merged", body)
        self.assertIn("/tmp/run.log", body)


def _config() -> AgentConfig:
    from pathlib import Path

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
        blocked_path_patterns=(".env", "secrets/*"),
        test_cmd="",
        lint_cmd="",
        stale_lock_seconds=7200,
        enable_planner=True,
        planner_model="ollama/qwen3-coder:30b",
        repo_context_max_files=80,
        repo_context_max_bytes=120000,
        planner_timeout_seconds=900,
        comment_plan=True,
    )
