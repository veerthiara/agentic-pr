import tempfile
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
