from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    args: Sequence[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        self.result = result
        command = " ".join(result.args)
        super().__init__(
            f"Command failed ({result.returncode}): {command}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def run(
    args: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
    timeout: int | None = None,
) -> CommandResult:
    command_env = None
    if env is not None:
        command_env = os.environ.copy()
        command_env.update(env)

    try:
        completed = subprocess.run(
            list(args),
            cwd=Path(cwd) if cwd else None,
            env=command_env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        result = CommandResult(args=list(args), returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        result = CommandResult(
            args=list(args),
            returncode=124,
            stdout=stdout,
            stderr=stderr + f"\nCommand timed out after {timeout} seconds.",
            timed_out=True,
        )
    if check and result.returncode != 0:
        raise CommandError(result)
    return result
