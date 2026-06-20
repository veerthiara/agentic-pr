import os
import tempfile
import time
import unittest
from pathlib import Path

from agentic_pr.lock import FileLock, LockAlreadyHeld


class FileLockTests(unittest.TestCase):
    def test_lock_acquire_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "agent.lock"
            lock = FileLock(lock_path)

            lock.acquire()
            self.assertTrue(lock_path.exists())

            lock.release()
            self.assertFalse(lock_path.exists())

    def test_lock_prevents_duplicate_acquire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "agent.lock"
            first = FileLock(lock_path)
            second = FileLock(lock_path)

            first.acquire()
            try:
                with self.assertRaises(LockAlreadyHeld):
                    second.acquire()
            finally:
                first.release()


    def test_stale_lock_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "agent.lock"
            lock_path.write_text("old")
            old_time = time.time() - 10
            os.utime(lock_path, (old_time, old_time))

            lock = FileLock(lock_path, stale_seconds=1, run_id="run-new")
            lock.acquire()
            try:
                self.assertIn("run-new", lock_path.read_text())
            finally:
                lock.release()
