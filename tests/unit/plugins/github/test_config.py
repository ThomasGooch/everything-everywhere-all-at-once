"""Unit tests for GitHub plugin configuration."""

import os
from unittest.mock import patch

import pytest

from plugins.github.config import GitHubConfig


class TestGitHubConfig:
    """Test cases for GitHubConfig class."""

    def test_init_with_all_params(self):
        """Test GitHubConfig initialization with all parameters."""
        config = GitHubConfig(
            token="test_token",
            repo_owner="test_owner",
            repo_name="test_repo",
            base_branch="develop",
        )

        assert config.token == "test_token"
        assert config.repo_owner == "test_owner"
        assert config.repo_name == "test_repo"
        assert config.base_branch == "develop"

    def test_init_with_defaults(self):
        """Test GitHubConfig initialization with default base_branch."""
        config = GitHubConfig(
            token="test_token", repo_owner="test_owner", repo_name="test_repo"
        )

        assert config.base_branch == "main"

    def test_repo_full_name_property(self):
        """Test repo_full_name property returns correct format."""
        config = GitHubConfig(
            token="test_token", repo_owner="test_owner", repo_name="test_repo"
        )

        assert config.repo_full_name == "test_owner/test_repo"

    def test_repo_url_property(self):
        """Test repo_url property returns HTTPS URL."""
        config = GitHubConfig(
            token="test_token", repo_owner="test_owner", repo_name="test_repo"
        )

        assert config.repo_url == "https://github.com/test_owner/test_repo.git"

    def test_repo_ssh_url_property(self):
        """Test repo_ssh_url property returns SSH URL."""
        config = GitHubConfig(
            token="test_token", repo_owner="test_owner", repo_name="test_repo"
        )

        assert config.repo_ssh_url == "git@github.com:test_owner/test_repo.git"

    @patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "env_token",
            "GITHUB_REPO_OWNER": "env_owner",
            "GITHUB_REPO_NAME": "env_repo",
            "GITHUB_BASE_BRANCH": "env_branch",
        },
    )
    def test_from_env_with_all_vars(self):
        """Test from_env with all environment variables set."""
        config = GitHubConfig.from_env()

        assert config is not None
        assert config.token == "env_token"
        assert config.repo_owner == "env_owner"
        assert config.repo_name == "env_repo"
        assert config.base_branch == "env_branch"

    @patch.dict(
        os.environ,
        {
            "GITHUB_API_TOKEN": "api_token",
            "GITHUB_OWNER": "alt_owner",
            "GITHUB_REPOSITORY": "alt_repo",
        },
        clear=True,
    )
    def test_from_env_with_alternative_vars(self):
        """Test from_env with alternative environment variable names."""
        config = GitHubConfig.from_env()

        assert config is not None
        assert config.token == "api_token"
        assert config.repo_owner == "alt_owner"
        assert config.repo_name == "alt_repo"
        assert config.base_branch == "main"  # Default value

    @patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "test_token",
            "GITHUB_REPO_OWNER": "test_owner"
            # Missing GITHUB_REPO_NAME
        },
        clear=True,
    )
    def test_from_env_missing_required_vars(self):
        """Test from_env returns None when required variables are missing."""
        config = GitHubConfig.from_env()

        assert config is None

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_no_vars(self):
        """Test from_env returns None when no environment variables are set."""
        config = GitHubConfig.from_env()

        assert config is None

    @patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "",
            "GITHUB_REPO_OWNER": "test_owner",
            "GITHUB_REPO_NAME": "test_repo",
        },
        clear=True,
    )
    def test_from_env_empty_required_var(self):
        """Test from_env returns None when required variable is empty."""
        config = GitHubConfig.from_env()

        assert config is None
