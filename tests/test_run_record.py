import json
import tempfile
import unittest
from pathlib import Path

from agentic_pr.run_record import RunRecord, latest_run_record, list_run_records, write_run_record


class RunRecordTests(unittest.TestCase):
    def test_run_record_json_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = RunRecord(
                run_id="run-20260619-150405-issue-7",
                issue_number=7,
                issue_title="Add min",
                owner_repo="octo/repo",
                model="ollama/qwen3-coder:30b",
                base_branch="main",
                agent_branch="agent/issue-7",
                status="pr_created",
                pr_url="https://example.test/pr/1",
                started_at="2026-06-19T15:04:05",
                finished_at="2026-06-19T15:05:05",
                log_file="/tmp/run.log",
                error_summary=None,
                planner_enabled=True,
                planner_status="completed",
                planner_output_file="/tmp/plan.md",
                plan_summary="Do the thing",
                planned_files_to_modify=["README.md"],
                planned_files_to_create=["main.py"],
                planned_test_plan="pytest",
            )

            path = write_run_record(Path(tmp), record)
            data = json.loads(path.read_text())

            self.assertEqual(path.name, "run-20260619-150405-issue-7.json")
            self.assertEqual(data["run_id"], record.run_id)
            self.assertEqual(data["status"], "pr_created")
            self.assertTrue(data["planner_enabled"])
            self.assertEqual(data["plan_summary"], "Do the thing")
            self.assertEqual(data["planned_files_to_create"], ["main.py"])
            self.assertEqual(list_run_records(Path(tmp)), [path])
            self.assertEqual(latest_run_record(Path(tmp)), path)

    def test_run_record_supports_pr_followup_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = RunRecord(
                run_id="run-20260620-120000-pr-5-c1",
                issue_number=0,
                issue_title="",
                owner_repo="octo/repo",
                model="ollama/qwen3-coder:30b",
                base_branch="main",
                agent_branch="agent/issue-5-123",
                status="pr_created",
                pr_url="https://example.test/pr/5",
                started_at="2026-06-20T12:00:00",
                finished_at="2026-06-20T12:05:00",
                log_file="/tmp/run.log",
                error_summary=None,
                run_type="pr_followup",
                pr_number=5,
                pr_title="Add FastAPI app",
                comment_id="c1",
                command_text="add tests",
                commit_sha="abc123",
            )

            path = write_run_record(Path(tmp), record)
            data = json.loads(path.read_text())

            self.assertEqual(data["run_type"], "pr_followup")
            self.assertEqual(data["pr_number"], 5)
            self.assertEqual(data["pr_title"], "Add FastAPI app")
            self.assertEqual(data["comment_id"], "c1")
            self.assertEqual(data["command_text"], "add tests")
            self.assertEqual(data["commit_sha"], "abc123")

    def test_run_record_supports_ci_followup_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = RunRecord(
                run_id="run-20260620-120000-pr-5-c1",
                issue_number=0,
                issue_title="",
                owner_repo="octo/repo",
                model="ollama/qwen3-coder:30b",
                base_branch="main",
                agent_branch="agent/issue-5-123",
                status="pr_updated",
                pr_url="https://example.test/pr/5",
                started_at="2026-06-20T12:00:00",
                finished_at="2026-06-20T12:05:00",
                log_file="/tmp/run.log",
                error_summary=None,
                run_type="pr_followup",
                pr_number=5,
                pr_title="Add FastAPI app",
                comment_id="c1",
                command_text="fix-ci",
                commit_sha="abc123",
                is_ci_fix=True,
                ci_checks_found=True,
                ci_failing_checks_found=True,
                ci_failed_check_names=["lint", "test"],
                ci_context_summary="Found 3 checks, 2 failing: lint, test",
                ci_log_excerpt="=== lint ===\nError: lint failed",
                ci_log_excerpt_file="/tmp/run-123-ci-context.md",
                ci_warnings=["Warning: logs truncated"],
            )

            path = write_run_record(Path(tmp), record)
            data = json.loads(path.read_text())

            self.assertEqual(data["run_type"], "pr_followup")
            self.assertTrue(data["is_ci_fix"])
            self.assertTrue(data["ci_checks_found"])
            self.assertTrue(data["ci_failing_checks_found"])
            self.assertEqual(data["ci_failed_check_names"], ["lint", "test"])
            self.assertEqual(data["ci_context_summary"], "Found 3 checks, 2 failing: lint, test")
            self.assertIn("lint failed", data["ci_log_excerpt"])
            self.assertEqual(data["ci_log_excerpt_file"], "/tmp/run-123-ci-context.md")
            self.assertEqual(data["ci_warnings"], ["Warning: logs truncated"])
