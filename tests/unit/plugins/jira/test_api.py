"""Unit tests for Jira API client."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from plugins.jira.api import JiraAPI


class TestJiraAPI:
    """Test cases for JiraAPI class."""

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_init_success(self, mock_from_env):
        """Test JiraAPI initialization with valid config."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        api = JiraAPI()
        assert api.config == mock_config

        # Verify auth header is created correctly
        expected_auth = base64.b64encode(
            "test@example.com:test_key".encode("ascii")
        ).decode("ascii")
        assert api.auth_header == expected_auth

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_init_no_config(self, mock_from_env):
        """Test JiraAPI initialization raises ValueError when no config."""
        mock_from_env.return_value = None

        with pytest.raises(ValueError, match="Jira configuration not available"):
            JiraAPI()

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_get_issue_sync_wrapper(self, mock_from_env):
        """Test sync wrapper for get_issue."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        api = JiraAPI()

        # Mock the async method to return expected data
        with patch.object(api, "get_issue_async") as mock_async:
            mock_async.return_value = {
                "key": "TEST-123",
                "fields": {"summary": "Test issue", "status": {"name": "In Progress"}},
            }

            result = api.get_issue("TEST-123")

        assert result["key"] == "TEST-123"
        assert result["fields"]["summary"] == "Test issue"

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_jira_auth_header_creation(self, mock_from_env):
        """Test that auth header is created correctly."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        api = JiraAPI()

        # Verify auth header is correct base64 encoding
        expected_auth = base64.b64encode(
            "test@example.com:test_key".encode("ascii")
        ).decode("ascii")
        assert api.auth_header == expected_auth

    @patch("plugins.jira.api.JiraConfig.from_env")
    @patch("asyncio.run")
    def test_get_issue_sync_wrapper(self, mock_run, mock_from_env):
        """Test sync wrapper for get_issue."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        mock_run.return_value = {"key": "TEST-123"}

        api = JiraAPI()
        result = api.get_issue("TEST-123")

        assert result["key"] == "TEST-123"
        mock_run.assert_called_once()

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_search_issues_mock_implementation(self, mock_from_env):
        """Test search issues returns mock data correctly."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        api = JiraAPI()
        result = api.search_issues("project = TEST", 25)

        # Test the mock implementation
        assert result["issues"] == []
        assert result["total"] == 0
        assert result["maxResults"] == 25

    @patch("plugins.jira.api.JiraConfig.from_env")
    def test_search_issues_sync(self, mock_from_env):
        """Test sync search issues (mock implementation)."""
        mock_config = MagicMock()
        mock_config.username = "test@example.com"
        mock_config.api_key = "test_key"
        mock_config.base_url = "https://test.atlassian.net"
        mock_from_env.return_value = mock_config

        api = JiraAPI()
        result = api.search_issues("project = TEST")

        # This is the mock implementation
        assert result["issues"] == []
        assert result["total"] == 0
        assert result["maxResults"] == 50
