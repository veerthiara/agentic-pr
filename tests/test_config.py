from pathlib import Path
import unittest

from agentic_pr.config import ConfigError, load_config, parse_env_file


class ConfigTests(unittest.TestCase):
    def test_parse_env_file_ignores_comments_and_unquotes(self) -> None:
        with self.subTest():
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                config_file = Path(tmp) / "agent.env"
                config_file.write_text(
                    """
# comment
OWNER_REPO="octo/repo"
BASE_BRANCH=main
"""
                )

                values = parse_env_file(config_file)

                self.assertEqual(values["OWNER_REPO"], "octo/repo")
                self.assertEqual(values["BASE_BRANCH"], "main")

    def test_load_config_requires_fields(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "agent.env"
            config_file.write_text("OWNER_REPO=octo/repo\n")

            with self.assertRaisesRegex(ConfigError, "Missing required config values"):
                load_config(config_file)

    def test_load_config_builds_typed_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            repo.mkdir()
            config_file = tmp_path / "agent.env"
            config_file.write_text(
                f"""
REPO_PATH={repo}
OWNER_REPO=octo/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434/
LOG_DIR=logs
RUN_DIR=var/run
POLL_INTERVAL_SECONDS=300
LOCK_FILE=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test.lock
AIDER_EXTRA_ARGS=--no-show-model-warnings --message "hello world"
"""
            )

            config = load_config(config_file)

            self.assertEqual(config.repo_path, repo.resolve())
            self.assertEqual(config.owner_repo, "octo/repo")
            self.assertEqual(config.ollama_api_base, "http://localhost:11434")
            self.assertEqual(config.log_dir, (repo / "logs").resolve())
            self.assertEqual(config.run_dir, (repo / "var" / "run").resolve())
            self.assertEqual(config.poll_interval_seconds, 300)
            self.assertEqual(
                config.lock_file,
                Path("/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test.lock").resolve(),
            )
            self.assertEqual(config.aider_extra_args, ("--no-show-model-warnings", "--message", "hello world"))

    def test_load_config_rejects_invalid_poll_interval(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            repo.mkdir()
            config_file = tmp_path / "agent.env"
            config_file.write_text(
                f"""
REPO_PATH={repo}
OWNER_REPO=octo/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
POLL_INTERVAL_SECONDS=0
"""
            )

            with self.assertRaisesRegex(ConfigError, "POLL_INTERVAL_SECONDS must be greater than zero"):
                load_config(config_file)
