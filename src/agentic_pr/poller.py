from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import sleep

from agentic_pr.config import AgentConfig
from agentic_pr.lock import FileLock, LockAlreadyHeld
from agentic_pr.orchestrator import RunResult, run_once


RunOnce = Callable[[AgentConfig], RunResult]
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


def poll_once(config: AgentConfig, *, run_once_fn: RunOnce = run_once, sleep_fn: SleepFn | None = None) -> RunResult | None:
    lock = FileLock(config.lock_file)
    try:
        lock.acquire()
    except LockAlreadyHeld as exc:
        message = f"Skipping cycle: {exc}"
        print(message)
        _log(config, message)
        if sleep_fn:
            sleep_fn(config.poll_interval_seconds)
        return None

    try:
        result = run_once_fn(config)
        _log(config, f"{result.status}: {result.message}")
        print(result.message)
        return result
    except Exception as exc:
        message = f"Polling cycle failed unexpectedly: {exc}"
        _log(config, message)
        print(message)
        return RunResult("failed", message)
    finally:
        lock.release()


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
