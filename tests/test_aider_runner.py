import unittest

from agentic_pr.aider_runner import build_prompt
from agentic_pr.github_ops import Issue


class AiderRunnerTests(unittest.TestCase):
    def test_prompt_generation(self) -> None:
        prompt = build_prompt(Issue(number=9, title="Fix docs", body="Please update README", created_at="2026-01-01"))

        self.assertIn("GitHub issue: #9", prompt)
        self.assertIn("Title: Fix docs", prompt)
        self.assertIn("Please update README", prompt)
