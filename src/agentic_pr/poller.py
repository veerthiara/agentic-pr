from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import sleep

from agentic_pr.config import AgentConfig
from agentic_pr.orchestrator import FollowupResult, RunResult, run_once, run_pr_followup_once


RunOnce = Callable[[AgentConfig], RunResult]
FollowupOnce = Callable[[AgentConfig], FollowupResult]
SleepFn = Callable[[int], None]


def poll_forever(config: AgentConfig) -> None:
    print_startup(config)
    try:
        while True:
            poll_once(config)
            sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        _log(config, "Polling stopped by Ctrl+C.")
        print("Polling stopped.")


def poll_once(config: AgentConfig, *, run_once_fn: RunOnce = run_once, run_followup_fn: FollowupOnce = run_pr_followup_once, sleep_fn: SleepFn | None = None) -> RunResult | FollowupResult | None:
    # Process issue task first
    try:
        result = run_once_fn(config)
        _log(config, f"{result.status}: {result.message}")
        print(result.message)
    except Exception as exc:
        message = f"Polling cycle (issue) failed unexpectedly: {exc}"
        _log(config, message)
        print(message)
        if sleep_fn:
            sleep_fn(config.poll_interval_seconds)
        return RunResult("failed", message)

    # Process PR follow-up task if enabled
    if config.enable_pr_followups:
        try:
            followup_result = run_followup_fn(config)
            if followup_result.status != "no_followup":
                _log(config, f"followup:{followup_result.status}: {followup_result.message}")
                print(followup_result.message)
                return followup_result
        except Exception as exc:
            message = f"Polling cycle (follow-up) failed unexpectedly: {exc}"
            _log(config, message)
            print(message)
            if sleep_fn:
                sleep_fn(config.poll_interval_seconds)
            return FollowupResult("failed", message)

    return result


def print_startup(config: AgentConfig) -> None:
    lines = [
        "Starting agentic-pr poller",
        f"repo: {config.repo_path}",
        f"owner repo: {config.owner_repo}",
        f"polling interval: {config.poll_interval_seconds}s",
        f"model: {config.model}",
        f"lock file: {config.lock_file}",
    ]
    for line in lines:
        print(line)
    _log(config, " | ".join(lines))


def _log(config: AgentConfig, message: str) -> None:
    config.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(config.log_dir) / "poller.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_file.open("a") as handle:
        handle.write(f"{timestamp} {message}\n")
