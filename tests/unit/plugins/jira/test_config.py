"""Unit tests for Jira plugin configuration."""

import os
from unittest.mock import patch

import pytest

from plugins.jira.config import JiraConfig


class TestJiraConfig:
    """Test cases for JiraConfig class."""

    def test_init_with_all_params(self):
        """Test JiraConfig initialization with all parameters."""
        config = JiraConfig(
            base_url="https://test.atlassian.net",
            api_key="test_key",
            username="test@example.com",
            project_key="TEST",
        )

        assert config.base_url == "https://test.atlassian.net"
        assert config.api_key == "test_key"
        assert config.username == "test@example.com"
        assert config.project_key == "TEST"

    @patch.dict(
        os.environ,
        {
            "JIRA_BASE_URL": "https://env.atlassian.net",
            "JIRA_API_KEY": "env_key",
            "JIRA_USERNAME": "env@example.com",
            "JIRA_PROJECT_KEY": "ENV",
        },
    )
    def test_from_env_with_all_vars(self):
        """Test from_env with all environment variables set."""
        config = JiraConfig.from_env()

        assert config is not None
        assert config.base_url == "https://env.atlassian.net"
        assert config.api_key == "env_key"
        assert config.username == "env@example.com"
        assert config.project_key == "ENV"

    @patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://alt.atlassian.net",
            "JIRA_API_TOKEN": "alt_token",
            "JIRA_EMAIL": "alt@example.com",
        },
        clear=True,
    )
    def test_from_env_with_alternative_vars(self):
        """Test from_env with alternative environment variable names."""
        config = JiraConfig.from_env()

        assert config is not None
        assert config.base_url == "https://alt.atlassian.net"
        assert config.api_key == "alt_token"
        assert config.username == "alt@example.com"
        assert config.project_key == "DEMO"  # Default value

    @patch.dict(
        os.environ,
        {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_API_KEY": "test_key"
            # Missing JIRA_USERNAME
        },
        clear=True,
    )
    def test_from_env_missing_required_vars(self):
        """Test from_env returns None when required variables are missing."""
        config = JiraConfig.from_env()

        assert config is None

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_no_vars(self):
        """Test from_env returns None when no environment variables are set."""
        config = JiraConfig.from_env()

        assert config is None
