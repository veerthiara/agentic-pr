from pathlib import Path
import tempfile
import unittest

from agentic_pr.config import ConfigError, load_config, parse_env_file


class ConfigTests(unittest.TestCase):
    def test_parse_env_file_ignores_comments_and_unquotes(self) -> None:
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
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "agent.env"
            config_file.write_text("OWNER_REPO=octo/repo\n")

            with self.assertRaisesRegex(ConfigError, "Missing required config values"):
                load_config(config_file)

    def test_load_config_builds_typed_config(self) -> None:
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
LABEL_NO_CHANGES=agent-no-changes
LABEL_BLOCKED=agent-blocked
OLLAMA_API_BASE=http://localhost:11434/
LOG_DIR=logs
RUN_DIR=var/run
POLL_INTERVAL_SECONDS=300
LOCK_FILE=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test.lock
RUN_RECORD_DIR=/Users/vsinghthiara/Developer/Learning/agentic-pr/var/runs
AGENT_HOST_LABEL=Mac Studio
COMMENT_ON_START=true
COMMENT_ON_SUCCESS=false
COMMENT_ON_FAILURE=true
COMMENT_ON_NO_CHANGES=true
AIDER_EXTRA_ARGS=--no-show-model-warnings --message "hello world"
AIDER_TIMEOUT_SECONDS=1800
MAX_CHANGED_FILES=20
MAX_DIFF_LINES=800
REQUIRE_AIDERIGNORE=true
BLOCKED_PATH_PATTERNS=.env,secrets/*
TEST_CMD=python -m unittest
LINT_CMD=python -m py_compile calc.py
STALE_LOCK_SECONDS=7200
ENABLE_PLANNER=true
PLANNER_MODEL=ollama/qwen3-coder:30b
REPO_CONTEXT_MAX_FILES=80
REPO_CONTEXT_MAX_BYTES=120000
PLANNER_TIMEOUT_SECONDS=900
COMMENT_PLAN=false
"""
            )

            config = load_config(config_file)

            self.assertEqual(config.repo_path, repo.resolve())
            self.assertEqual(config.owner_repo, "octo/repo")
            self.assertEqual(config.ollama_api_base, "http://localhost:11434")
            self.assertEqual(config.log_dir, (repo / "logs").resolve())
            self.assertEqual(config.run_dir, (repo / "var" / "run").resolve())
            self.assertEqual(config.poll_interval_seconds, 300)
            self.assertEqual(config.label_no_changes, "agent-no-changes")
            self.assertEqual(config.label_blocked, "agent-blocked")
            self.assertEqual(
                config.lock_file,
                Path("/Users/vsinghthiara/Developer/Learning/agentic-pr/var/run/agent-test.lock").resolve(),
            )
            self.assertEqual(
                config.run_record_dir,
                Path("/Users/vsinghthiara/Developer/Learning/agentic-pr/var/runs").resolve(),
            )
            self.assertEqual(config.agent_host_label, "Mac Studio")
            self.assertTrue(config.comment_on_start)
            self.assertFalse(config.comment_on_success)
            self.assertTrue(config.comment_on_failure)
            self.assertTrue(config.comment_on_no_changes)
            self.assertEqual(config.aider_extra_args, ("--no-show-model-warnings", "--message", "hello world"))
            self.assertEqual(config.aider_timeout_seconds, 1800)
            self.assertEqual(config.max_changed_files, 20)
            self.assertEqual(config.max_diff_lines, 800)
            self.assertTrue(config.require_aiderignore)
            self.assertEqual(config.blocked_path_patterns, (".env", "secrets/*"))
            self.assertEqual(config.test_cmd, "python -m unittest")
            self.assertEqual(config.lint_cmd, "python -m py_compile calc.py")
            self.assertEqual(config.stale_lock_seconds, 7200)
            self.assertTrue(config.enable_planner)
            self.assertEqual(config.planner_model, "ollama/qwen3-coder:30b")
            self.assertEqual(config.repo_context_max_files, 80)
            self.assertEqual(config.repo_context_max_bytes, 120000)
            self.assertEqual(config.planner_timeout_seconds, 900)
            self.assertFalse(config.comment_plan)

    def test_load_config_rejects_invalid_poll_interval(self) -> None:
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

    def test_load_config_rejects_invalid_comment_bool(self) -> None:
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
COMMENT_ON_START=maybe
"""
            )

            with self.assertRaisesRegex(ConfigError, "COMMENT_ON_START must be true or false"):
                load_config(config_file)

    def test_load_config_includes_ci_fields(self) -> None:
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
ENABLE_CI_CONTEXT=true
CI_COMMAND_ALIASES=/agent fix-ci,/agent fix checks
CI_LOG_MAX_LINES=250
CI_LOG_MAX_BYTES=40000
CI_INCLUDE_SUCCESSFUL_CHECKS=false
CI_REQUIRE_FAILED_CHECKS=false
"""
            )

            config = load_config(config_file)

            self.assertTrue(config.enable_ci_context)
            self.assertEqual(config.ci_command_aliases, ("/agent fix-ci", "/agent fix checks"))
            self.assertEqual(config.ci_log_max_lines, 250)
            self.assertEqual(config.ci_log_max_bytes, 40000)
            self.assertFalse(config.ci_include_successful_checks)
            self.assertFalse(config.ci_require_failed_checks)

    def test_load_config_includes_repo_instructions_fields(self) -> None:
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
ENABLE_REPO_INSTRUCTIONS=true
REPO_INSTRUCTIONS_DIR=.agentic-pr
REPO_INSTRUCTIONS_MAX_BYTES=50000
"""
            )

            config = load_config(config_file)

            self.assertTrue(config.enable_repo_instructions)
            self.assertEqual(config.repo_instructions_dir, ".agentic-pr")
            self.assertEqual(config.repo_instructions_max_bytes, 50000)

    def test_load_config_includes_maintenance_fields(self) -> None:
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
RUN_RETENTION_DAYS=60
LOG_RETENTION_DAYS=45
PROMPT_RETENTION_DAYS=30
COMMENT_STATE_RETENTION_DAYS=90
MAX_LOG_PREVIEW_LINES=100
SERVICE_LABEL=com.veer.agentic-pr.test
"""
            )

            config = load_config(config_file)

            self.assertEqual(config.run_retention_days, 60)
            self.assertEqual(config.log_retention_days, 45)
            self.assertEqual(config.prompt_retention_days, 30)
            self.assertEqual(config.comment_state_retention_days, 90)
            self.assertEqual(config.max_log_preview_lines, 100)
            self.assertEqual(config.service_label, "com.veer.agentic-pr.test")
