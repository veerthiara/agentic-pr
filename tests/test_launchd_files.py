from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LaunchdFileTests(unittest.TestCase):
    def test_launchd_template_contains_expected_service_shape(self) -> None:
        template = (ROOT / "launchd/com.veer.agentic-pr.agent-test.plist.template").read_text()

        self.assertIn("com.veer.agentic-pr.agent-test", template)
        self.assertIn("bin/run-poller-launchd.sh", template)
        self.assertIn("__CONFIG_PATH__", template)
        self.assertIn("logs/launchd.out.log", template)
        self.assertIn("logs/launchd.err.log", template)

    def test_service_scripts_exist(self) -> None:
        for relative_path in (
            "bin/run-poller-launchd.sh",
            "bin/install-launchd.sh",
            "bin/uninstall-launchd.sh",
            "bin/service-status.sh",
        ):
            self.assertTrue((ROOT / relative_path).exists(), relative_path)
