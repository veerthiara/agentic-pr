from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agentic_pr.ci import CheckResult, get_failing_checks, get_pr_checks, get_workflow_run_logs
from agentic_pr.config import AgentConfig


@dataclass(frozen=True)
class CIContext:
    """CI context for Aider prompt."""
    checks_found: bool
    failing_checks_found: bool
    summary: str
    failed_check_names: list[str]
    log_excerpt: str
    warnings: list[str]


def build_ci_context(config: AgentConfig, pr_number: int) -> CIContext:
    """
    Build CI context for a PR.
    
    Collects check status and log excerpts for failing checks.
    """
    warnings = []
    
    # Get all checks
    all_checks = get_pr_checks(config, pr_number)
    checks_found = len(all_checks) > 0
    
    if not checks_found:
        return CIContext(
            checks_found=False,
            failing_checks_found=False,
            summary="No GitHub checks found for this PR.",
            failed_check_names=[],
            log_excerpt="",
            warnings=["No checks found - CI context unavailable"],
        )
    
    # Get failing checks
    failing_checks = get_failing_checks(config, pr_number)
    failing_checks_found = len(failing_checks) > 0
    failed_check_names = [check.name for check in failing_checks]
    
    if not failing_checks_found:
        summary = f"Found {len(all_checks)} check(s), all passing."
        if config.ci_require_failed_checks:
            warnings.append("CI_REQUIRE_FAILED_CHECKS=true but no failing checks found")
        return CIContext(
            checks_found=True,
            failing_checks_found=False,
            summary=summary,
            failed_check_names=[],
            log_excerpt="",
            warnings=warnings,
        )
    
    # Collect log excerpts from failing checks
    log_parts = []
    for check in failing_checks:
        log_part = f"\n=== {check.name} ===\n"
        
        if check.workflow_run_id:
            logs = get_workflow_run_logs(
                config,
                check.workflow_run_id,
                config.ci_log_max_lines,
                config.ci_log_max_bytes,
            )
            log_part += logs
        elif check.check_run_id:
            # Could add check run logs here if needed
            log_part += f"Check run ID: {check.check_run_id} (logs not fetched via check run API)"
        else:
            log_part += "No workflow run ID or check run ID available for log fetching."
        
        log_parts.append(log_part)
    
    log_excerpt = "\n".join(log_parts)
    
    # Build summary
    summary = (
        f"Found {len(all_checks)} check(s), {len(failing_checks)} failing: "
        f"{', '.join(failed_check_names)}"
    )
    
    return CIContext(
        checks_found=True,
        failing_checks_found=True,
        summary=summary,
        failed_check_names=failed_check_names,
        log_excerpt=log_excerpt,
        warnings=warnings,
    )