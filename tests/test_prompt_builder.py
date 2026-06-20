import unittest

from agentic_pr.github_ops import Issue
from agentic_pr.planner import PlannerResult
from agentic_pr.prompt_builder import build_implementation_prompt


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_includes_issue_plan_and_file_creation_permission(self) -> None:
        issue = Issue(number=1, title="Build app", body="Make a FastAPI app", created_at="now")
        plan = PlannerResult(True, "completed", "Summary\nBuild routes", None, "Build routes", ["main.py"], ["tests/test_app.py"], "pytest", None)

        prompt = build_implementation_prompt(issue=issue, run_id="run-1", planner_result=plan)

        self.assertIn("Make a FastAPI app", prompt)
        self.assertIn("Build routes", prompt)
        self.assertIn("Creating new files is allowed", prompt)
        self.assertIn("Run ID: run-1", prompt)
