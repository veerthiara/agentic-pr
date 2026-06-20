import tempfile
import unittest
from pathlib import Path

from agentic_pr.command import run
from agentic_pr.repo_context import build_repo_context


class RepoContextTests(unittest.TestCase):
    def test_repo_context_ignores_generated_and_secret_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init"], cwd=repo)
            (repo / "README.md").write_text("hello")
            (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
            (repo / "calc.py").write_text("def add(a,b): return a+b\n")
            (repo / ".env").write_text("SECRET=x")
            (repo / "node_modules").mkdir()
            (repo / "node_modules/pkg.js").write_text("x")
            (repo / ".venv").mkdir()
            (repo / ".venv/pyvenv.cfg").write_text("x")
            (repo / "tests").mkdir()
            (repo / "tests/test_calc.py").write_text("def test_ok(): pass\n")

            context = build_repo_context(repo, max_files=80, max_bytes=120000)

            self.assertIn("README.md", context.important_files)
            self.assertIn("pyproject.toml", context.important_files)
            self.assertIn("calc.py", context.important_files)
            self.assertIn("tests/test_calc.py", context.important_files)
            self.assertNotIn(".env", context.important_files)
            self.assertFalse(any(path.startswith("node_modules") for path in context.important_files))
            self.assertFalse(any(path.startswith(".venv") for path in context.important_files))
