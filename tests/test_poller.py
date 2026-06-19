import tempfile
import unittest
from pathlib import Path

from agentic_pr.config import AgentConfig
from agentic_pr.orchestrator import RunResult
from agentic_pr.poller import poll_once


class PollerTests(unittest.TestCase):
    def test_poll_once_runs_one_iteration_and_releases_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            calls = []

            def fake_run_once(received_config: AgentConfig) -> RunResult:
                calls.append(received_config)
                return RunResult("no_issue", "No issue")

            result = poll_once(config, run_once_fn=fake_run_once)

            self.assertEqual(result, RunResult("no_issue", "No issue"))
            self.assertEqual(calls, [config])
            self.assertFalse(config.lock_file.exists())
            self.assertIn("no_issue: No issue", (config.log_dir / "poller.log").read_text())

    def test_poll_once_skips_when_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            config.lock_file.parent.mkdir(parents=True)
            config.lock_file.write_text("pid=123\n")
            calls = []
            sleeps = []

            def fake_run_once(received_config: AgentConfig) -> RunResult:
                calls.append(received_config)
                return RunResult("pr_created", "Created")

            result = poll_once(config, run_once_fn=fake_run_once, sleep_fn=sleeps.append)

            self.assertIsNone(result)
            self.assertEqual(calls, [])
            self.assertEqual(sleeps, [config.poll_interval_seconds])
            self.assertTrue(config.lock_file.exists())


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
        ollama_api_base="http://localhost:11434",
        aider_extra_args=(),
        log_dir=root / "logs",
        run_dir=root / "run",
        poll_interval_seconds=60,
        lock_file=root / "run" / "agent.lock",
    )
