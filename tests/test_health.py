import unittest
from unittest.mock import patch, MagicMock

from agentic_pr.health import get_health_summary, HealthCheck
from agentic_pr.config import AgentConfig


class HealthTests(unittest.TestCase):
    def test_check_config(self) -> None:
        # Test with valid config
        config = MagicMock()
        config.repo_path = "/tmp/repo"
        config.owner_repo = "owner/repo"
        
        check = get_health_summary(config)
        self.assertEqual(check.checks[0].name, "config")
        self.assertEqual(check.checks[0].status, "ok")

    def test_check_config_missing_values(self) -> None:
        # Test with invalid config
        config = MagicMock()
        config.repo_path = None
        config.owner_repo = None
        
        check = get_health_summary(config)
        self.assertEqual(check.checks[0].name, "config")
        self.assertEqual(check.checks[0].status, "fail")

    @patch("agentic_pr.health.run")
    def test_check_gh_exists(self, mock_run) -> None:
        # Test that gh command exists
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        check = get_health_summary(MagicMock())
        self.assertEqual(check.checks[3].name, "gh")
        self.assertEqual(check.checks[3].status, "ok")

    @patch("agentic_pr.health.run")
    def test_check_gh_missing(self, mock_run) -> None:
        # Test that gh command doesn't exist
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="command not found")
        
        check = get_health_summary(MagicMock())
        self.assertEqual(check.checks[3].name, "gh")
        self.assertEqual(check.checks[3].status, "fail")

    @patch("agentic_pr.health.run")
    def test_check_ollama(self, mock_run) -> None:
        # Test that ollama API responds
        import requests
        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            
            check = get_health_summary(MagicMock())
            self.assertEqual(check.checks[7].name, "ollama")
            self.assertEqual(check.checks[7].status, "ok")

    @patch("agentic_pr.health.run")
    def test_check_ollama_fails(self, mock_run) -> None:
        # Test that ollama API fails
        import requests
        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 500
            
            check = get_health_summary(MagicMock())
            self.assertEqual(check.checks[7].name, "ollama")
            self.assertEqual(check.checks[7].status, "fail")

    def test_overall_status_ok(self) -> None:
        # Test that overall status is ok when all checks pass
        config = MagicMock()
        config.repo_path = "/tmp/repo"
        config.owner_repo = "owner/repo"
        
        check = get_health_summary(config)
        self.assertEqual(check.overall_status, "ok")

    def test_overall_status_warn(self) -> None:
        # Test that overall status is warn when one check fails
        config = MagicMock()
        config.repo_path = "/tmp/repo"
        config.owner_repo = "owner/repo"
        
        with patch("agentic_pr.health.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            
            check = get_health_summary(config)
            # The first check (config) should pass, but the gh check should fail
            self.assertEqual(check.overall_status, "fail")

    def test_overall_status_fail(self) -> None:
        # Test that overall status is fail when one check fails
        config = MagicMock()
        config.repo_path = None
        config.owner_repo = None
        
        check = get_health_summary(config)
        self.assertEqual(check.overall_status, "fail")