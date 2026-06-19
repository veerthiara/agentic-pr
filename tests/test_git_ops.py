import unittest

from agentic_pr.git_ops import branch_name


class GitOpsTests(unittest.TestCase):
    def test_branch_name_generation(self) -> None:
        self.assertEqual(branch_name(42, "20260617010101"), "agent/issue-42-20260617010101")
