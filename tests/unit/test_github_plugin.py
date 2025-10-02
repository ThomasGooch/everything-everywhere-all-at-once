"""Unit tests for GitHub plugin - TDD Implementation"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from core.plugin_interface import PluginStatus, PluginType
from plugins.github_plugin import GitHubPlugin


class TestGitHubPlugin:
    """Test GitHub plugin functionality using TDD approach"""

    @pytest.fixture
    def github_config(self):
        """Test configuration for GitHub plugin"""
        return {
            "type": "version_control",
            "provider": "github",
            "connection": {
                "token": "ghp_test_token_123",
                "api_url": "https://api.github.com",
            },
            "mappings": {
                "repository": "full_name",
                "branch": "ref",
                "commit_hash": "sha",
                "commit_message": "commit.message",
                "pull_request": "html_url",
            },
            "options": {
                "timeout": 60,
                "retry_attempts": 3,
                "default_branch": "main",
                "auto_create_branches": True,
                "require_pr_reviews": True,
                "merge_strategy": "squash",
            },
        }

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_github_plugin_initialization(self, github_config):
        """Test GitHubPlugin basic initialization"""
        plugin = GitHubPlugin(github_config)

        assert plugin.get_plugin_type() == PluginType.VERSION_CONTROL
        assert plugin.get_plugin_name() == "github"
        assert plugin.get_version() == "1.0.0"
        assert plugin.config == github_config
        assert not plugin._is_initialized
        assert not plugin._connection_established

    def test_github_plugin_config_validation_success(self, github_config):
        """Test successful configuration validation"""
        plugin = GitHubPlugin(github_config)

        assert plugin.validate_config() is True

    def test_github_plugin_config_validation_missing_token(self, github_config):
        """Test configuration validation with missing token"""
        del github_config["connection"]["token"]
        plugin = GitHubPlugin(github_config)

        with pytest.raises(Exception):  # Will be PluginValidationError
            plugin.validate_config()

    def test_github_plugin_config_validation_invalid_token_format(self, github_config):
        """Test configuration validation with invalid token format"""
        github_config["connection"]["token"] = "invalid_token_format"
        plugin = GitHubPlugin(github_config)

        with pytest.raises(Exception):  # Will be PluginValidationError
            plugin.validate_config()

    def test_required_config_keys(self):
        """Test required configuration keys"""
        plugin = GitHubPlugin({})
        required_keys = plugin.get_required_config_keys()

        assert "connection.token" in required_keys
        assert "connection.api_url" in required_keys

    def test_optional_config_keys(self):
        """Test optional configuration keys"""
        plugin = GitHubPlugin({})
        optional_keys = plugin.get_optional_config_keys()

        assert "options.timeout" in optional_keys
        assert "options.retry_attempts" in optional_keys
        assert "options.default_branch" in optional_keys
        assert "options.merge_strategy" in optional_keys

    @pytest.mark.asyncio
    async def test_github_plugin_initialization_success(self, github_config):
        """Test successful plugin initialization"""
        plugin = GitHubPlugin(github_config)

        # Mock GitHub API authentication test
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"login": "testuser", "id": 12345})

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        with patch("plugins.github_plugin.ClientSession", return_value=mock_session):
            success = await plugin.initialize()

            assert success is True
            assert plugin._is_initialized is True
            assert plugin._connection_established is True

    @pytest.mark.asyncio
    async def test_github_plugin_initialization_failure(self, github_config):
        """Test failed plugin initialization due to auth error"""
        plugin = GitHubPlugin(github_config)

        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        with patch("plugins.github_plugin.ClientSession", return_value=mock_session):
            # Mock failed authentication
            mock_session.get.side_effect = Exception("Authentication failed")

            success = await plugin.initialize()

            assert success is False
            assert plugin._is_initialized is False
            assert plugin._connection_established is False

    @pytest.mark.asyncio
    async def test_clone_repository_success(self, github_config, temp_workspace):
        """Test successful repository cloning"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        repo_url = "https://github.com/testorg/testrepo.git"
        local_path = str(temp_workspace / "testrepo")

        with patch("plugins.github_plugin.git.Repo.clone_from") as mock_clone:
            mock_repo = Mock()
            mock_repo.active_branch.name = "main"
            mock_repo.git_dir = str(temp_workspace / ".git")
            mock_repo.iter_commits.return_value = [Mock(), Mock(), Mock()]  # 3 commits
            mock_clone.return_value = mock_repo

            result = await plugin.clone_repository(repo_url, local_path)

            assert result.success is True
            assert result.data["repository_url"] == repo_url
            assert result.data["local_path"] == local_path
            assert result.data["commit_count"] == 3
            mock_clone.assert_called_once_with(repo_url, local_path)

    @pytest.mark.asyncio
    async def test_clone_repository_failure(self, github_config, temp_workspace):
        """Test repository cloning failure"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        repo_url = "https://github.com/nonexistent/repo.git"
        local_path = str(temp_workspace / "repo")

        with patch("plugins.github_plugin.git.Repo.clone_from") as mock_clone:
            mock_clone.side_effect = Exception("Repository not found")

            result = await plugin.clone_repository(repo_url, local_path)

            assert result.success is False
            assert "Repository not found" in result.error

    @pytest.mark.asyncio
    async def test_create_branch_success(self, github_config, temp_workspace):
        """Test successful branch creation"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        # Setup mock repository
        repo_path = str(temp_workspace)
        branch_name = "feature/test-branch"
        base_branch = "main"

        with patch("plugins.github_plugin.git.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.heads = {"main": Mock()}
            mock_repo.create_head.return_value = Mock()

            result = await plugin.create_branch(repo_path, branch_name, base_branch)

            assert result.success is True
            assert result.data["branch_name"] == branch_name
            assert result.data["base_branch"] == base_branch
            mock_repo.create_head.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_changes_success(self, github_config, temp_workspace):
        """Test successful commit creation"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        repo_path = str(temp_workspace)
        commit_message = "Test commit message"
        files = ["file1.py", "file2.py"]

        with patch("plugins.github_plugin.git.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_commit = Mock()
            mock_commit.hexsha = "abc123def456"
            mock_repo.index.commit.return_value = mock_commit

            result = await plugin.commit_changes(repo_path, commit_message, files)

            assert result.success is True
            assert result.data["commit_hash"] == "abc123def456"
            assert result.data["message"] == commit_message
            assert result.data["files"] == files

    @pytest.mark.asyncio
    async def test_push_branch_success(self, github_config, temp_workspace):
        """Test successful branch push"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        repo_path = str(temp_workspace)
        branch_name = "feature/test-branch"

        with patch("plugins.github_plugin.git.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # Mock remotes properly
            mock_remote = Mock()
            mock_push_info = Mock()
            mock_push_info.flags = 0  # No error flags
            mock_push_info.summary = "success"
            mock_remote.push.return_value = [mock_push_info]
            mock_repo.remotes.origin = mock_remote
            mock_repo.remotes.__contains__ = Mock(
                return_value=True
            )  # 'origin' in remotes
            mock_repo.remotes.__getitem__ = Mock(
                return_value=mock_remote
            )  # repo.remotes['origin']

            result = await plugin.push_branch(repo_path, branch_name)

            assert result.success is True
            assert result.data["branch_name"] == branch_name
            mock_remote.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self, github_config, temp_workspace):
        """Test successful pull request creation"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        # Setup mock session
        mock_session = MagicMock()
        plugin._session = mock_session
        plugin._api_url = "https://api.github.com"

        pr_data = {
            "title": "Test PR",
            "body": "Test PR description",
            "head": "feature/test-branch",
            "base": "main",
            "repository": "testorg/testrepo",
        }

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(
            return_value={
                "html_url": "https://github.com/testorg/testrepo/pull/123",
                "number": 123,
                "id": 987654,
                "title": "Test PR",
                "state": "open",
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.create_pull_request(temp_workspace, pr_data)

        assert result.success is True
        assert result.data["pr_url"] == "https://github.com/testorg/testrepo/pull/123"
        assert result.data["pr_number"] == 123

    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, github_config):
        """Test successful repository info retrieval"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        # Setup mock session
        mock_session = MagicMock()
        plugin._session = mock_session
        plugin._api_url = "https://api.github.com"

        repo_name = "testorg/testrepo"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "full_name": "testorg/testrepo",
                "name": "testrepo",
                "owner": {"login": "testorg"},
                "default_branch": "main",
                "clone_url": "https://github.com/testorg/testrepo.git",
                "ssh_url": "git@github.com:testorg/testrepo.git",
                "private": False,
                "description": "Test repository",
                "language": "Python",
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        result = await plugin.get_repository_info(repo_name)

        assert result.success is True
        assert result.data["full_name"] == "testorg/testrepo"
        assert result.data["default_branch"] == "main"

    @pytest.mark.asyncio
    async def test_get_repository_info_not_found(self, github_config):
        """Test repository info retrieval for non-existent repo"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Repository not found")

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        result = await plugin.get_repository_info("nonexistent/repo")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, github_config):
        """Test health check when service is healthy"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session
        plugin._api_url = "https://api.github.com"

        mock_response = MagicMock()
        mock_response.status = 200

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager

        status = await plugin.health_check()

        assert status == PluginStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, github_config):
        """Test health check when service is unhealthy"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._connection_established = False

        status = await plugin.health_check()

        assert status == PluginStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_cleanup_success(self, github_config):
        """Test successful plugin cleanup"""
        plugin = GitHubPlugin(github_config)
        plugin._is_initialized = True
        plugin._session = AsyncMock()

        success = await plugin.cleanup()

        assert success is True
        assert plugin._is_initialized is False
        assert plugin._session is None

    def test_get_repository_owner_and_name(self, github_config):
        """Test repository owner/name extraction from various formats"""
        plugin = GitHubPlugin(github_config)

        # Test different repository URL formats
        test_cases = [
            ("testorg/testrepo", ("testorg", "testrepo")),
            ("https://github.com/testorg/testrepo", ("testorg", "testrepo")),
            ("https://github.com/testorg/testrepo.git", ("testorg", "testrepo")),
            ("git@github.com:testorg/testrepo.git", ("testorg", "testrepo")),
        ]

        for repo_input, expected in test_cases:
            owner, name = plugin._parse_repository_identifier(repo_input)
            assert (owner, name) == expected

    def test_validate_branch_name(self, github_config):
        """Test branch name validation"""
        plugin = GitHubPlugin(github_config)

        # Valid branch names
        valid_names = [
            "main",
            "develop",
            "feature/test",
            "bugfix/issue-123",
            "release/v1.0.0",
            "hotfix/critical-fix",
        ]

        for name in valid_names:
            assert plugin._validate_branch_name(name) is True

        # Invalid branch names
        invalid_names = [
            "",
            "  ",
            "feature..test",
            "branch with spaces",
            "branch~with^special*chars",
            ".branch",
            "branch.",
        ]

        for name in invalid_names:
            assert plugin._validate_branch_name(name) is False
