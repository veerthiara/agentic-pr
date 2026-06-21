from __future__ import annotations

import argparse
import json
import sys

from agentic_pr.config import ConfigError, load_config
from agentic_pr.doctor import run_doctor
from agentic_pr.github_ops import ensure_labels
from agentic_pr.orchestrator import run_once, run_pr_followup_once
from agentic_pr.poller import poll_forever
from agentic_pr.run_record import latest_run_record, list_run_records, load_run_record
from agentic_pr.ci import get_pr_checks, get_failing_checks, get_workflow_run_logs
from agentic_pr.run_history import list_runs, get_last_run, get_run, summarize_run
from agentic_pr.health import get_health_summary
from agentic_pr.maintenance import run_cleanup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentic-pr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("doctor", "ensure-labels", "run-once", "run-followup-once", "poll", "list-runs", "show-last-run", "ci-summary", "health", "cleanup"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--config", required=True)
        if name == "ci-summary":
            command_parser.add_argument("--pr", type=int, required=True)
        elif name == "show-run":
            command_parser.add_argument("--run-id", required=True)
        elif name == "cleanup":
            command_parser.add_argument("--dry-run", action="store_true")
            command_parser.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.command == "doctor":
            for message in run_doctor(config):
                print(message)
        elif args.command == "ensure-labels":
            ensure_labels(config)
            print("ok: labels ensured")
        elif args.command == "run-once":
            result = run_once(config)
            print(result.message)
            return 1 if result.status == "failed" else 0
        elif args.command == "run-followup-once":
            result = run_pr_followup_once(config)
            print(result.message)
            return 1 if result.status == "failed" else 0
        elif args.command == "poll":
            poll_forever(config)
        elif args.command == "list-runs":
            runs = list_runs(config, limit=20)
            for run in runs:
                print(f"{run.run_id} | {run.status} | {run.issue_number or run.pr_number} | {run.started_at}")
        elif args.command == "show-last-run":
            last_run = get_last_run(config)
            if last_run is None:
                print("No run records found.")
            else:
                print(summarize_run(last_run))
        elif args.command == "show-run":
            run = get_run(config, args.run_id)
            if run is None:
                print(f"Run {args.run_id} not found.")
            else:
                print(summarize_run(run))
        elif args.command == "health":
            health = get_health_summary(config)
            print(f"Overall status: {health.overall_status}")
            for check in health.checks:
                print(f"  {check.name}: {check.status} - {check.message}")
            if health.latest_run:
                print("\nLatest run:")
                print(json.dumps(health.latest_run, indent=2, sort_keys=True))
        elif args.command == "cleanup":
            if args.dry_run and args.apply:
                print("error: --dry-run and --apply cannot be used together")
                return 1
            dry_run = True if args.dry_run else False
            run_cleanup(config, dry_run=dry_run)
        elif args.command == "ci-summary":
            checks = get_pr_checks(config, args.pr)
            if not checks:
                print(f"No checks found for PR #{args.pr}")
                return 0
            
            print(f"Checks for PR #{args.pr}:")
            for check in checks:
                status = check.get("state", "unknown")
                conclusion = check.get("conclusion", "pending")
                name = check.get("name", "unknown")
                print(f"  - {name}: {status} ({conclusion})")
            
            failing = get_failing_checks(config, args.pr)
            if failing:
                print(f"\nFailing checks ({len(failing)}):")
                for check in failing:
                    name = check.get("name", "unknown")
                    run_id = check.get("workflowRunId")
                    print(f"  - {name} (run_id: {run_id})")
                    if run_id:
                        logs = get_workflow_run_logs(config, run_id)
                        if logs:
                            print(f"    Logs:\n{logs[:2000]}")
                            if len(logs) > 2000:
                                print("    ... [truncated]")
        return 0
    except (ConfigError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
