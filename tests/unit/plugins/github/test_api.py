"""Unit tests for GitHub API client."""

import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from plugins.github.api import GitHubAPI
from plugins.github.config import GitHubConfig


class TestGitHubAPI:
    """Test cases for GitHubAPI class."""

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_init_success(self, mock_from_env):
        """Test GitHubAPI initialization with valid config."""
        mock_config = MagicMock()
        mock_config.token = "test_token"
        mock_config.repo_owner = "test_owner"
        mock_config.repo_name = "test_repo"
        mock_from_env.return_value = mock_config

        api = GitHubAPI()
        assert api.config == mock_config

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_init_no_config(self, mock_from_env):
        """Test GitHubAPI initialization raises ValueError when no config."""
        mock_from_env.return_value = None

        with pytest.raises(ValueError, match="GitHub configuration not available"):
            GitHubAPI()

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("shutil.rmtree")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_clone_repository_success(
        self, mock_exists, mock_subprocess, mock_rmtree, mock_from_env
    ):
        """Test successful repository cloning."""
        mock_config = MagicMock()
        mock_config.repo_ssh_url = "git@github.com:owner/repo.git"
        mock_config.repo_url = "https://github.com/owner/repo.git"
        mock_from_env.return_value = mock_config

        mock_subprocess.return_value = MagicMock()
        mock_exists.return_value = True

        api = GitHubAPI()
        target_dir = Path("/tmp/test_repo")

        result = api.clone_repository(target_dir, use_ssh=True)

        assert result["success"] is True
        assert result["repo_url"] == "git@github.com:owner/repo.git"
        mock_rmtree.assert_called_once_with(target_dir)
        mock_subprocess.assert_called_once_with(
            ["git", "clone", "git@github.com:owner/repo.git", str(target_dir)],
            check=True,
        )

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_clone_repository_failure(
        self, mock_exists, mock_subprocess, mock_from_env
    ):
        """Test repository cloning failure."""
        mock_config = MagicMock()
        mock_config.repo_ssh_url = "git@github.com:owner/repo.git"
        mock_from_env.return_value = mock_config

        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")
        mock_exists.return_value = False

        api = GitHubAPI()
        target_dir = Path("/tmp/test_repo")

        result = api.clone_repository(target_dir)

        assert result["success"] is False
        assert "error" in result

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("subprocess.run")
    def test_create_branch_success(self, mock_subprocess, mock_from_env):
        """Test successful branch creation."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        mock_subprocess.return_value = MagicMock()

        api = GitHubAPI()
        workspace_dir = Path("/tmp/workspace")
        branch_name = "feature-branch"

        result = api.create_branch(workspace_dir, branch_name)

        assert result["success"] is True
        assert result["branch"] == "feature-branch"
        mock_subprocess.assert_called_once_with(
            ["git", "checkout", "-b", "feature-branch"], cwd=workspace_dir, check=True
        )

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("subprocess.run")
    def test_commit_changes_success(self, mock_subprocess, mock_from_env):
        """Test successful commit of changes."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        # Mock git status showing changes
        mock_status_result = MagicMock()
        mock_status_result.stdout = " M file1.py\n A file2.py\n"

        mock_subprocess.side_effect = [
            mock_status_result,  # git status
            MagicMock(),  # git add
            MagicMock(),  # git commit
        ]

        api = GitHubAPI()
        workspace_dir = Path("/tmp/workspace")
        commit_message = "Test commit"

        result = api.commit_changes(workspace_dir, commit_message)

        assert result["success"] is True
        assert result["changes"] is True
        assert result["commit_message"] == "Test commit"
        assert result["files_changed"] == 2

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("subprocess.run")
    def test_commit_changes_no_changes(self, mock_subprocess, mock_from_env):
        """Test commit when no changes are present."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        # Mock git status showing no changes
        mock_status_result = MagicMock()
        mock_status_result.stdout = ""
        mock_subprocess.return_value = mock_status_result

        api = GitHubAPI()
        workspace_dir = Path("/tmp/workspace")
        commit_message = "Test commit"

        result = api.commit_changes(workspace_dir, commit_message)

        assert result["success"] is True
        assert result["changes"] is False
        assert "No changes to commit" in result["message"]

    @patch("plugins.github.api.GitHubConfig.from_env")
    @patch("subprocess.run")
    def test_push_branch_success(self, mock_subprocess, mock_from_env):
        """Test successful branch push."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        mock_subprocess.return_value = MagicMock()

        api = GitHubAPI()
        workspace_dir = Path("/tmp/workspace")
        branch_name = "feature-branch"

        result = api.push_branch(workspace_dir, branch_name)

        assert result["success"] is True
        assert result["branch"] == "feature-branch"
        mock_subprocess.assert_called_once_with(
            ["git", "push", "-u", "origin", "feature-branch"],
            cwd=workspace_dir,
            check=True,
        )

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_create_pull_request_sync(self, mock_from_env):
        """Test sync wrapper for PR creation."""
        mock_config = MagicMock()
        mock_config.repo_full_name = "owner/repo"
        mock_config.token = "test_token"
        mock_config.base_branch = "main"
        mock_from_env.return_value = mock_config

        api = GitHubAPI()

        # Mock the async method to return success
        with patch.object(api, "create_pull_request_async") as mock_async:
            mock_async.return_value = {
                "success": True,
                "pr_number": 123,
                "pr_url": "https://github.com/owner/repo/pull/123",
            }

            result = api.create_pull_request("feature-branch", "Test PR", "Test body")

        assert result["success"] is True
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/owner/repo/pull/123"

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_generate_branch_name(self, mock_from_env):
        """Test branch name generation."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        api = GitHubAPI()

        with patch("time.time", return_value=1234567890):
            branch_name = api.generate_branch_name("TASK-123", "user authentication")

        assert branch_name.startswith("TASK-123_user_authentication_")
        assert len(branch_name.split("_")[-1]) == 6  # timestamp should be 6 digits

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_generate_commit_message(self, mock_from_env):
        """Test commit message generation."""
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        api = GitHubAPI()
        message = api.generate_commit_message(
            "TASK-123", "Implement user authentication"
        )

        expected = "TASK-123: Implement user authentication\n\n🤖 Generated with automated workflow"
        assert message == expected

    @patch("plugins.github.api.GitHubConfig.from_env")
    def test_generate_pr_body(self, mock_from_env):
        """Test PR body generation."""
        mock_config = MagicMock()
        mock_config.repo_full_name = "owner/repo"
        mock_from_env.return_value = mock_config

        api = GitHubAPI()
        task_details = {
            "fields": {
                "summary": "Implement user authentication",
                "description": "Add login and registration features",
            }
        }

        body = api.generate_pr_body("TASK-123", task_details)

        assert "## Summary" in body
        assert "TASK-123" in body
        assert "Implement user authentication" in body
        assert "Add login and registration features" in body
        assert "🤖 Generated with" in body
