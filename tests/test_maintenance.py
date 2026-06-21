import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from agentic_pr.maintenance import plan_cleanup, run_cleanup, CleanupItem
from agentic_pr.config import AgentConfig


class MaintenanceTests(unittest.TestCase):
    def test_plan_cleanup_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.run_record_dir = Path(tmp)
            config.log_dir = Path(tmp)
            config.run_dir = Path(tmp)
            config.comment_state_dir = Path(tmp)
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            items = plan_cleanup(config)
            self.assertEqual(len(items), 0)

    def test_plan_cleanup_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create directories but no files
            run_record_dir = Path(tmp) / "runs"
            log_dir = Path(tmp) / "logs"
            run_dir = Path(tmp) / "run"
            comment_state_dir = Path(tmp) / "comment-state"
            
            run_record_dir.mkdir()
            log_dir.mkdir()
            run_dir.mkdir()
            comment_state_dir.mkdir()
            
            config = MagicMock()
            config.run_record_dir = run_record_dir
            config.log_dir = log_dir
            config.run_dir = run_dir
            config.comment_state_dir = comment_state_dir
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            items = plan_cleanup(config)
            self.assertEqual(len(items), 0)

    def test_plan_cleanup_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a run record file
            run_record_dir = Path(tmp) / "runs"
            run_record_dir.mkdir()
            record_file = run_record_dir / "run-123.json"
            record_file.write_text('{"run_id":"run-123","issue_number":1,"status":"pr_created"}')
            
            config = MagicMock()
            config.run_record_dir = run_record_dir
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 0  # Should clean up immediately
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            items = plan_cleanup(config)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].path, record_file)
            self.assertEqual(items[0].category, "run_records")

    @patch("agentic_pr.maintenance._should_cleanup_file")
    def test_plan_cleanup_with_should_cleanup(self, mock_should_cleanup) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a run record file
            run_record_dir = Path(tmp) / "runs"
            run_record_dir.mkdir()
            record_file = run_record_dir / "run-123.json"
            record_file.write_text('{"run_id":"run-123","issue_number":1,"status":"pr_created"}')
            
            config = MagicMock()
            config.run_record_dir = run_record_dir
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            # Mock to always return True for cleanup
            mock_should_cleanup.return_value = True
            
            items = plan_cleanup(config)
            self.assertEqual(len(items), 1)

    def test_run_cleanup_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a run record file
            run_record_dir = Path(tmp) / "runs"
            run_record_dir.mkdir()
            record_file = run_record_dir / "run-123.json"
            record_file.write_text('{"run_id":"run-123","issue_number":1,"status":"pr_created"}')
            
            config = MagicMock()
            config.run_record_dir = run_record_dir
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 0  # Should clean up immediately
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            items = run_cleanup(config, dry_run=True)
            self.assertEqual(len(items), 1)

    def test_run_cleanup_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a run record file
            run_record_dir = Path(tmp) / "runs"
            run_record_dir.mkdir()
            record_file = run_record_dir / "run-123.json"
            record_file.write_text('{"run_id":"run-123","issue_number":1,"status":"pr_created"}')
            
            config = MagicMock()
            config.run_record_dir = run_record_dir
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 0  # Should clean up immediately
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            items = run_cleanup(config, dry_run=False)
            self.assertEqual(len(items), 1)
            # File should be deleted
            self.assertFalse(record_file.exists())

    def test_should_not_cleanup_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.run_record_dir = Path(tmp) / "runs"
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            # Test that source files are not cleaned up
            test_file = Path(tmp) / "README.md"
            test_file.touch()
            
            # This should return False for source files
            from agentic_pr.maintenance import _should_cleanup_file
            result = _should_cleanup_file(test_file, 30, config)
            self.assertFalse(result)

    def test_should_not_cleanup_config_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.run_record_dir = Path(tmp) / "runs"
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            # Test that config files are not cleaned up
            test_file = Path(tmp) / "config" / "agent-test.env"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.touch()
            
            # This should return False for config files
            from agentic_pr.maintenance import _should_cleanup_file
            result = _should_cleanup_file(test_file, 30, config)
            self.assertFalse(result)

    def test_should_not_cleanup_lock_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.run_record_dir = Path(tmp) / "runs"
            config.log_dir = Path(tmp) / "logs"
            config.run_dir = Path(tmp) / "run"
            config.comment_state_dir = Path(tmp) / "comment-state"
            config.lock_file = Path(tmp) / "agent.lock"
            config.run_retention_days = 30
            config.log_retention_days = 30
            config.prompt_retention_days = 30
            config.comment_state_retention_days = 90
            
            # Test that lock files are not cleaned up (unless stale)
            test_file = Path(tmp) / "agent.lock"
            test_file.touch()
            
            # This should return False for lock files (unless they're stale)
            from agentic_pr.maintenance import _should_cleanup_file
            result = _should_cleanup_file(test_file, 30, config)
            self.assertFalse(result)