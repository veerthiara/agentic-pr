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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentic-pr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("doctor", "ensure-labels", "run-once", "run-followup-once", "poll", "list-runs", "show-last-run", "ci-summary"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--config", required=True)
        if name == "ci-summary":
            command_parser.add_argument("--pr", type=int, required=True)

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
            for path in list_run_records(config.run_record_dir):
                print(path)
        elif args.command == "show-last-run":
            path = latest_run_record(config.run_record_dir)
            if path is None:
                print("No run records found.")
            else:
                print(json.dumps(load_run_record(path), indent=2, sort_keys=True))
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
