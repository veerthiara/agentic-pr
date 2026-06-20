import unittest

from agentic_pr.git_ops import branch_name


class GitOpsTests(unittest.TestCase):
    def test_branch_name_generation(self) -> None:
        self.assertEqual(branch_name(42, "20260617010101"), "agent/issue-42-20260617010101")

    def test_changed_files_and_diff_line_count(self) -> None:
        import tempfile
        from pathlib import Path
        from agentic_pr.command import run
        from agentic_pr.git_ops import changed_files, diff_line_count

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init"], cwd=repo)
            (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")

            self.assertEqual(changed_files(repo), ["calc.py"])
            self.assertEqual(diff_line_count(repo), 2)
