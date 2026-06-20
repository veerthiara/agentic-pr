from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class LockAlreadyHeld(RuntimeError):
    pass


@dataclass(frozen=True)
class FileLock:
    path: Path
    stale_seconds: int | None = None
    run_id: str | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self._is_stale():
            self.path.unlink()
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(self.path, flags)
        except FileExistsError as exc:
            raise LockAlreadyHeld(f"Lock already exists: {self.path}") from exc
        with os.fdopen(fd, "w") as lock_file:
            json.dump({"pid": os.getpid(), "run_id": self.run_id, "started_at": datetime.now().isoformat(timespec="seconds")}, lock_file)
            lock_file.write("\n")

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def _is_stale(self) -> bool:
        if self.stale_seconds is None:
            return False
        age = datetime.now().timestamp() - self.path.stat().st_mtime
        return age > self.stale_seconds

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()
