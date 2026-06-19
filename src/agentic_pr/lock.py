from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class LockAlreadyHeld(RuntimeError):
    pass


@dataclass(frozen=True)
class FileLock:
    path: Path

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(self.path, flags)
        except FileExistsError as exc:
            raise LockAlreadyHeld(f"Lock already exists: {self.path}") from exc
        with os.fdopen(fd, "w") as lock_file:
            lock_file.write(f"pid={os.getpid()}\n")

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()
