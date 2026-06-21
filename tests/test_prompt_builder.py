import unittest

from agentic_pr.github_ops import Issue
from agentic_pr.planner import PlannerResult
from agentic_pr.pr_followup import FollowupTask
from agentic_pr.prompt_builder import build_implementation_prompt, build_followup_prompt


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_includes_issue_plan_and_file_creation_permission(self) -> None:
        issue = Issue(number=1, title="Build app", body="Make a FastAPI app", created_at="now")
        plan = PlannerResult(True, "completed", "Summary\nBuild routes", None, "Build routes", ["main.py"], ["tests/test_app.py"], "pytest", None)

        prompt = build_implementation_prompt(issue=issue, run_id="run-1", planner_result=plan)

        self.assertIn("Make a FastAPI app", prompt)
        self.assertIn("Build routes", prompt)
        self.assertIn("Creating new files is allowed", prompt)
        self.assertIn("Run ID: run-1", prompt)

    def test_followup_prompt_includes_pr_info_and_no_new_pr_instruction(self) -> None:
        task = FollowupTask(
            pr_number=5,
            pr_title="Add FastAPI app",
            comment_id="c1",
            comment_author="user1",
            comment_body="/agent add tests",
            command_text="add tests",
            head_branch="agent/issue-5-123",
            base_branch="main",
            pr_url="https://github.com/octo/repo/pull/5",
        )
        plan = PlannerResult(True, "completed", "Summary\nAdd tests", None, "Add tests", ["tests/test_app.py"], [], "pytest", None)

        prompt = build_followup_prompt(task=task, run_id="run-2", planner_result=plan)

        self.assertIn("PR: #5", prompt)
        self.assertIn("Add FastAPI app", prompt)
        self.assertIn("add tests", prompt)
        self.assertIn("Run ID: run-2", prompt)
        self.assertIn("Do NOT create a new branch or PR", prompt)
        self.assertIn("Preserve the existing PR intent", prompt)
        self.assertIn("Make the smallest additional change", prompt)
