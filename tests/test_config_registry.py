import tempfile
import unittest
from pathlib import Path

from agentic_pr.config_registry import (
    RepoConfigRef,
    discover_configs,
    get_config_by_name,
    list_config_summaries,
    _is_safe_name,
)


class ConfigRegistryTests(unittest.TestCase):
    def test_is_safe_name(self) -> None:
        self.assertTrue(_is_safe_name("agent-test"))
        self.assertTrue(_is_safe_name("my_repo"))
        self.assertTrue(_is_safe_name("repo123"))
        self.assertFalse(_is_safe_name(""))
        self.assertFalse(_is_safe_name("my repo"))  # space
        self.assertFalse(_is_safe_name("../etc"))  # path traversal
        self.assertFalse(_is_safe_name(".hidden"))  # starts with dot
        self.assertFalse(_is_safe_name("a/b"))  # slash

    def test_no_config_repos_folder_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Don't create config/repos
            configs = discover_configs(root)
            self.assertEqual(configs, [])

    def test_discovers_config_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            # Create a valid config
            config_file = repos_dir / "agent-test.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
ENABLED=true
""")
            
            configs = discover_configs(root)
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].name, "agent-test")
            self.assertEqual(configs[0].owner_repo, "owner/repo")
            self.assertEqual(configs[0].base_branch, "main")
            self.assertTrue(configs[0].enabled)

    def test_disabled_config_ignored_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            config_file = repos_dir / "disabled-repo.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
ENABLED=false
""")
            
            configs = discover_configs(root)
            self.assertEqual(len(configs), 0)
            
            configs_with_disabled = discover_configs(root, include_disabled=True)
            self.assertEqual(len(configs_with_disabled), 1)
            self.assertFalse(configs_with_disabled[0].enabled)

    def test_include_disabled_returns_disabled_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            config_file = repos_dir / "disabled-repo.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
ENABLED=false
""")
            
            configs = discover_configs(root, include_disabled=True)
            self.assertEqual(len(configs), 1)
            self.assertFalse(configs[0].enabled)

    def test_unsafe_names_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            # Create config with unsafe name
            config_file = repos_dir / "bad name.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
""")
            
            configs = discover_configs(root)
            self.assertEqual(len(configs), 0)

    def test_get_config_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            config_file = repos_dir / "my-repo.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
""")
            
            ref = get_config_by_name(root, "my-repo")
            self.assertIsNotNone(ref)
            if ref:
                self.assertEqual(ref.name, "my-repo")
                self.assertEqual(ref.owner_repo, "owner/repo")
                self.assertEqual(ref.base_branch, "main")

    def test_get_config_by_name_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref = get_config_by_name(root, "nonexistent")
            self.assertIsNone(ref)

    def test_get_config_by_name_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref = get_config_by_name(root, "../etc")
            self.assertIsNone(ref)

    def test_list_config_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_dir = root / "config" / "repos"
            repos_dir.mkdir(parents=True)
            
            config_file = repos_dir / "test-repo.env"
            config_file.write_text("""
REPO_PATH=/tmp/repo
OWNER_REPO=owner/repo
BASE_BRANCH=main
MODEL=ollama/qwen3-coder:30b
LABEL_TODO=agent-run
LABEL_RUNNING=agent-running
LABEL_DONE=agent-pr-created
LABEL_FAILED=agent-failed
OLLAMA_API_BASE=http://localhost:11434
ENABLED=true
""")
            
            summaries = list_config_summaries(root)
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["name"], "test-repo")
            self.assertEqual(summaries[0]["owner_repo"], "owner/repo")
            # On macOS /tmp resolves to /private/tmp, so check both
            self.assertIn(summaries[0]["repo_path"], ["/tmp/repo", "/private/tmp/repo"])
            self.assertEqual(summaries[0]["base_branch"], "main")
            self.assertTrue(summaries[0]["enabled"])