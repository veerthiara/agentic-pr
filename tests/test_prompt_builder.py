import unittest

from agentic_pr.github_ops import Issue
from agentic_pr.planner import PlannerResult
from agentic_pr.pr_followup import FollowupTask
from agentic_pr.prompt_builder import build_implementation_prompt, build_followup_prompt
from agentic_pr.ci_context import CIContext
from agentic_pr.repo_instructions import RepoInstructions


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_includes_issue_plan_and_file_creation_permission(self) -> None:
        issue = Issue(number=1, title="Build app", body="Make a FastAPI app", created_at="now")
        plan = PlannerResult(True, "completed", "Summary\nBuild routes", None, "Build routes", ["main.py"], ["tests/test_app.py"], "pytest", None)

        prompt = build_implementation_prompt(issue=issue, run_id="run-1", planner_result=plan)

        self.assertIn("Make a FastAPI app", prompt)
        self.assertIn("Build routes", prompt)
        self.assertIn("Creating new files is allowed", prompt)
        self.assertIn("Run ID: run-1", prompt)

    def test_prompt_includes_repo_instructions(self) -> None:
        issue = Issue(number=1, title="Build app", body="Make a FastAPI app", created_at="now")
        plan = PlannerResult(True, "completed", "Summary\nBuild routes", None, "Build routes", ["main.py"], ["tests/test_app.py"], "pytest", None)
        instructions = RepoInstructions(
            instructions_text="Test instructions",
            safety_text="Test safety",
            examples_text="Test examples",
            commands={"TEST_CMD": "pytest"}
        )

        prompt = build_implementation_prompt(issue=issue, run_id="run-1", planner_result=plan, repo_instructions=instructions)

        self.assertIn("Project Instructions:\nTest instructions", prompt)
        self.assertIn("Safety Rules:\nTest safety", prompt)
        self.assertIn("Examples:\nTest examples", prompt)
        self.assertIn("TEST_CMD: pytest", prompt)

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

    def test_followup_prompt_ci_fix_includes_ci_context(self) -> None:
        task = FollowupTask(
            pr_number=5,
            pr_title="Add FastAPI app",
            comment_id="c1",
            comment_author="user1",
            comment_body="/agent fix-ci",
            command_text="fix-ci",
            head_branch="agent/issue-5-123",
            base_branch="main",
            pr_url="https://github.com/octo/repo/pull/5",
            is_ci_fix=True,
            ci_command_alias="/agent fix-ci",
        )
        plan = PlannerResult(True, "completed", "Summary\nFix CI", None, "Fix CI", ["tests/test_app.py"], [], "pytest", None)
        ci_context = CIContext(
            checks_found=True,
            failing_checks_found=True,
            summary="Found 2 checks, 1 failing: lint",
            failed_check_names=["lint"],
            log_excerpt="=== lint ===\nError: lint failed\n  at file.py:10",
            warnings=[],
        )

        prompt = build_followup_prompt(task=task, run_id="run-3", planner_result=plan, ci_context=ci_context)

        self.assertIn("CI Context:", prompt)
        self.assertIn("Found 2 checks, 1 failing: lint", prompt)
        self.assertIn("lint", prompt)
        self.assertIn("Error: lint failed", prompt)
        self.assertIn("Fix the root cause of the failing CI checks", prompt)
        self.assertIn("Do not remove tests just to make CI pass", prompt)
        self.assertIn("Do not weaken assertions unless clearly correct", prompt)

    def test_followup_prompt_ci_fix_no_checks_found(self) -> None:
        task = FollowupTask(
            pr_number=5,
            pr_title="Add FastAPI app",
            comment_id="c1",
            comment_author="user1",
            comment_body="/agent fix-ci",
            command_text="fix-ci",
            head_branch="agent/issue-5-123",
            base_branch="main",
            pr_url="https://github.com/octo/repo/pull/5",
            is_ci_fix=True,
            ci_command_alias="/agent fix-ci",
        )
        plan = PlannerResult(True, "completed", "Summary\nFix CI", None, "Fix CI", ["tests/test_app.py"], [], "pytest", None)
        ci_context = CIContext(
            checks_found=False,
            failing_checks_found=False,
            summary="No GitHub checks found for this PR.",
            failed_check_names=[],
            log_excerpt="",
            warnings=["No checks found - CI context unavailable"],
        )

        prompt = build_followup_prompt(task=task, run_id="run-4", planner_result=plan, ci_context=ci_context)

        self.assertIn("CI Context:", prompt)
        self.assertIn("No GitHub checks found for this PR", prompt)
        self.assertIn("Fix the root cause of the failing CI checks", prompt)

    def test_followup_prompt_generic_not_ci_fix(self) -> None:
        task = FollowupTask(
            pr_number=5,
            pr_title="Add FastAPI app",
            comment_id="c1",
            comment_author="user1",
            comment_body="/agent update README",
            command_text="update README",
            head_branch="agent/issue-5-123",
            base_branch="main",
            pr_url="https://github.com/octo/repo/pull/5",
            is_ci_fix=False,
            ci_command_alias=None,
        )
        plan = PlannerResult(True, "completed", "Summary\nUpdate README", None, "Update README", ["README.md"], [], "pytest", None)

        prompt = build_followup_prompt(task=task, run_id="run-5", planner_result=plan)

        self.assertNotIn("CI Context:", prompt)
        self.assertNotIn("Fix the root cause of the failing CI checks", prompt)
        self.assertNotIn("Do not remove tests just to make CI pass", prompt)
