import sys
import unittest

from agentic_pr.command import CommandError, run


class CommandTests(unittest.TestCase):
    def test_run_captures_stdout(self) -> None:
        result = run([sys.executable, "-c", "print('hello')"])

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "hello\n")
        self.assertEqual(result.stderr, "")

    def test_run_raises_useful_error(self) -> None:
        with self.assertRaises(CommandError) as caught:
            run([sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"])

        self.assertEqual(caught.exception.result.returncode, 7)
        self.assertIn("bad", caught.exception.result.stderr)
