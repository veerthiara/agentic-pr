from __future__ import annotations

import argparse
import sys

from agentic_pr.config import ConfigError, load_config
from agentic_pr.doctor import run_doctor
from agentic_pr.github_ops import ensure_labels
from agentic_pr.orchestrator import run_once
from agentic_pr.poller import poll_forever


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentic-pr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("doctor", "ensure-labels", "run-once", "poll"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--config", required=True)

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
        elif args.command == "poll":
            poll_forever(config)
        return 0
    except (ConfigError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
