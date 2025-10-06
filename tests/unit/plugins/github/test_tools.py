"""Unit tests for GitHub tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.github.tools import (
    GitHubTools,
    complete_github_workflow,
    complete_github_workflow_async,
    setup_workspace,
)


class TestGitHubTools:
    """Test cases for GitHubTools class."""

    @patch("plugins.github.tools.GitHubAPI")
    def test_init(self, mock_github_api):
        """Test GitHubTools initialization."""
        tools = GitHubTools()
        mock_github_api.assert_called_once()

    @patch("plugins.github.tools.GitHubAPI")
    def test_setup_repository_workspace_success(self, mock_github_api):
        """Test successful repository workspace setup."""
        mock_api = MagicMock()
        mock_api.clone_repository.return_value = {
            "success": True,
            "repo_url": "test_url",
        }
        mock_api.generate_branch_name.return_value = "TASK-123_implementation_123456"
        mock_api.create_branch.return_value = {
            "success": True,
            "branch": "TASK-123_implementation_123456",
        }
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        target_dir = Path("/tmp/test")

        result = tools.setup_repository_workspace(
            target_dir, "TASK-123", "implementation"
        )

        assert result["success"] is True
        assert result["workspace_dir"] == target_dir
        assert result["branch_name"] == "TASK-123_implementation_123456"
        assert result["repo_url"] == "test_url"

        mock_api.clone_repository.assert_called_once_with(target_dir)
        mock_api.generate_branch_name.assert_called_once_with(
            "TASK-123", "implementation"
        )
        mock_api.create_branch.assert_called_once_with(
            target_dir, "TASK-123_implementation_123456"
        )

    @patch("plugins.github.tools.GitHubAPI")
    def test_setup_repository_workspace_clone_failure(self, mock_github_api):
        """Test workspace setup when clone fails."""
        mock_api = MagicMock()
        mock_api.clone_repository.return_value = {
            "success": False,
            "error": "Clone failed",
        }
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        target_dir = Path("/tmp/test")

        result = tools.setup_repository_workspace(
            target_dir, "TASK-123", "implementation"
        )

        assert result["success"] is False
        assert "Clone failed" in result["error"]

    @patch("plugins.github.tools.GitHubAPI")
    def test_setup_repository_workspace_branch_failure(self, mock_github_api):
        """Test workspace setup when branch creation fails."""
        mock_api = MagicMock()
        mock_api.clone_repository.return_value = {
            "success": True,
            "repo_url": "test_url",
        }
        mock_api.generate_branch_name.return_value = "test_branch"
        mock_api.create_branch.return_value = {
            "success": False,
            "error": "Branch creation failed",
        }
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        target_dir = Path("/tmp/test")

        result = tools.setup_repository_workspace(
            target_dir, "TASK-123", "implementation"
        )

        assert result["success"] is False
        assert "Branch creation failed" in result["error"]

    @patch("plugins.github.tools.GitHubAPI")
    @pytest.mark.asyncio
    async def test_complete_workflow_async_success(self, mock_github_api):
        """Test successful workflow completion."""
        mock_api = MagicMock()
        mock_api.generate_commit_message.return_value = "TASK-123: Test commit"
        mock_api.commit_changes.return_value = {
            "success": True,
            "changes": True,
            "commit_message": "TASK-123: Test commit",
            "files_changed": 3,
        }
        mock_api.push_branch.return_value = {"success": True, "branch": "test_branch"}
        mock_api.generate_pr_body.return_value = "Test PR body"
        mock_api.create_pull_request_async = AsyncMock(
            return_value={
                "success": True,
                "pr_number": 123,
                "pr_url": "https://github.com/owner/repo/pull/123",
            }
        )
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        workspace_dir = Path("/tmp/workspace")
        task_details = {"fields": {"summary": "Test implementation"}}

        result = await tools.complete_workflow_async(
            workspace_dir, "test_branch", "TASK-123", task_details
        )

        assert result["success"] is True
        assert result["changes"] is True
        assert result["commit_message"] == "TASK-123: Test commit"
        assert result["files_changed"] == 3
        assert result["branch_name"] == "test_branch"
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/owner/repo/pull/123"

    @patch("plugins.github.tools.GitHubAPI")
    @pytest.mark.asyncio
    async def test_complete_workflow_async_no_changes(self, mock_github_api):
        """Test workflow completion when no changes are present."""
        mock_api = MagicMock()
        mock_api.generate_commit_message.return_value = "TASK-123: Test commit"
        mock_api.commit_changes.return_value = {"success": True, "changes": False}
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        workspace_dir = Path("/tmp/workspace")

        result = await tools.complete_workflow_async(
            workspace_dir, "test_branch", "TASK-123"
        )

        assert result["success"] is True
        assert result["changes"] is False
        assert "No changes to commit" in result["message"]

    @patch("plugins.github.tools.GitHubAPI")
    @pytest.mark.asyncio
    async def test_complete_workflow_async_commit_failure(self, mock_github_api):
        """Test workflow completion when commit fails."""
        mock_api = MagicMock()
        mock_api.generate_commit_message.return_value = "TASK-123: Test commit"
        mock_api.commit_changes.return_value = {
            "success": False,
            "error": "Commit failed",
        }
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        workspace_dir = Path("/tmp/workspace")

        result = await tools.complete_workflow_async(
            workspace_dir, "test_branch", "TASK-123"
        )

        assert result["success"] is False
        assert "Commit failed" in result["error"]

    @patch("plugins.github.tools.GitHubAPI")
    def test_get_repository_info(self, mock_github_api):
        """Test getting repository information."""
        mock_config = MagicMock()
        mock_config.repo_owner = "test_owner"
        mock_config.repo_name = "test_repo"
        mock_config.repo_full_name = "test_owner/test_repo"
        mock_config.base_branch = "main"
        mock_config.repo_url = "https://github.com/test_owner/test_repo.git"
        mock_config.repo_ssh_url = "git@github.com:test_owner/test_repo.git"

        mock_api = MagicMock()
        mock_api.config = mock_config
        mock_github_api.return_value = mock_api

        tools = GitHubTools()
        info = tools.get_repository_info()

        assert info["repo_owner"] == "test_owner"
        assert info["repo_name"] == "test_repo"
        assert info["repo_full_name"] == "test_owner/test_repo"
        assert info["base_branch"] == "main"
        assert info["repo_url"] == "https://github.com/test_owner/test_repo.git"
        assert info["repo_ssh_url"] == "git@github.com:test_owner/test_repo.git"

    @patch("plugins.github.tools.GitHubAPI")
    @patch("subprocess.run")
    def test_check_workspace_changes_with_changes(
        self, mock_subprocess, mock_github_api
    ):
        """Test checking workspace changes when changes exist."""
        mock_github_api.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = " M file1.py\n A file2.py\n"
        mock_subprocess.return_value = mock_result

        tools = GitHubTools()
        workspace_dir = Path("/tmp/workspace")

        result = tools.check_workspace_changes(workspace_dir)

        assert result["success"] is True
        assert result["has_changes"] is True
        assert result["num_changes"] == 2
        assert len(result["changes"]) == 2

    @patch("plugins.github.tools.GitHubAPI")
    @patch("subprocess.run")
    def test_check_workspace_changes_no_changes(self, mock_subprocess, mock_github_api):
        """Test checking workspace changes when no changes exist."""
        mock_github_api.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        tools = GitHubTools()
        workspace_dir = Path("/tmp/workspace")

        result = tools.check_workspace_changes(workspace_dir)

        assert result["success"] is True
        assert result["has_changes"] is False
        assert result["num_changes"] == 0
        assert len(result["changes"]) == 0


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    @patch("plugins.github.tools.GitHubTools")
    def test_setup_workspace(self, mock_tools_class):
        """Test setup_workspace convenience function."""
        mock_tools = MagicMock()
        mock_tools.setup_repository_workspace.return_value = {"success": True}
        mock_tools_class.return_value = mock_tools

        target_dir = Path("/tmp/test")
        result = setup_workspace(target_dir, "TASK-123", "implementation")

        assert result["success"] is True
        mock_tools.setup_repository_workspace.assert_called_once_with(
            target_dir, "TASK-123", "implementation"
        )

    @patch("plugins.github.tools.GitHubTools")
    @pytest.mark.asyncio
    async def test_complete_github_workflow_async(self, mock_tools_class):
        """Test complete_github_workflow_async convenience function."""
        mock_tools = MagicMock()
        mock_tools.complete_workflow_async = AsyncMock(return_value={"success": True})
        mock_tools_class.return_value = mock_tools

        workspace_dir = Path("/tmp/workspace")
        result = await complete_github_workflow_async(
            workspace_dir, "test_branch", "TASK-123", {"test": "details"}
        )

        assert result["success"] is True
        mock_tools.complete_workflow_async.assert_called_once_with(
            workspace_dir, "test_branch", "TASK-123", {"test": "details"}
        )

    @patch("plugins.github.tools.GitHubTools")
    def test_complete_github_workflow_sync(self, mock_tools_class):
        """Test complete_github_workflow convenience function (sync)."""
        mock_tools = MagicMock()
        mock_tools.complete_workflow.return_value = {"success": True}
        mock_tools_class.return_value = mock_tools

        workspace_dir = Path("/tmp/workspace")
        result = complete_github_workflow(
            workspace_dir, "test_branch", "TASK-123", {"test": "details"}
        )

        assert result["success"] is True
        mock_tools.complete_workflow.assert_called_once_with(
            workspace_dir, "test_branch", "TASK-123", {"test": "details"}
        )
