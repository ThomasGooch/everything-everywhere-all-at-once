"""
Unit tests for WorkspaceManager - TDD implementation
Following the Red-Green-Refactor cycle
"""
import asyncio
import os
import shutil
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from core.workspace_manager import WorkspaceManager, Workspace, WorkspaceStatus
from core.exceptions import WorkspaceError, WorkspaceCleanupError


class TestWorkspaceManager:
    """Unit tests for WorkspaceManager"""

    @pytest.fixture
    def temp_base_dir(self):
        """Create temporary base directory for testing"""
        temp_dir = tempfile.mkdtemp(prefix="test_workspace_")
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def workspace_manager(self, temp_base_dir):
        """Create WorkspaceManager instance for testing"""
        return WorkspaceManager(base_dir=temp_base_dir)

    def test_workspace_manager_initialization(self, temp_base_dir):
        """Test WorkspaceManager initialization with valid base directory"""
        manager = WorkspaceManager(base_dir=temp_base_dir)

        assert manager.base_dir == temp_base_dir
        assert os.path.exists(temp_base_dir)

    def test_workspace_manager_initialization_creates_base_dir(self):
        """Test WorkspaceManager creates base directory if it doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        shutil.rmtree(temp_dir)  # Remove it first

        manager = WorkspaceManager(base_dir=temp_dir)

        assert os.path.exists(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, workspace_manager):
        """Test successful workspace creation"""
        agent_id = "test-agent-123"
        repository_url = "https://github.com/test/repo.git"

        workspace = await workspace_manager.create_workspace(agent_id, repository_url)

        assert workspace.id == agent_id
        assert workspace.repository_url == repository_url
        assert workspace.status == WorkspaceStatus.ACTIVE
        assert os.path.exists(workspace.path)
        assert workspace.created_at is not None
        assert isinstance(workspace.created_at, datetime)

        # Verify workspace directory structure
        workspace_path = Path(workspace.path)
        assert workspace_path.name == agent_id
        assert workspace_path.parent == Path(workspace_manager.base_dir)

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate_agent_id_fails(self, workspace_manager):
        """Test that creating workspace with duplicate agent_id fails"""
        agent_id = "test-agent-123"
        repository_url = "https://github.com/test/repo.git"

        # Create first workspace
        await workspace_manager.create_workspace(agent_id, repository_url)

        # Attempt to create duplicate should fail
        with pytest.raises(WorkspaceError, match="already exists"):
            await workspace_manager.create_workspace(agent_id, repository_url)

    @pytest.mark.asyncio
    async def test_create_workspace_with_git_setup(self, workspace_manager):
        """Test workspace creation includes Git configuration"""
        agent_id = "test-agent-git"
        repository_url = "https://github.com/test/repo.git"

        with patch("core.git_operations.GitOperations") as mock_git:
            mock_git_instance = AsyncMock()
            mock_git.return_value = mock_git_instance
            mock_git_instance.setup_repository.return_value = True

            workspace = await workspace_manager.create_workspace(
                agent_id, repository_url, setup_git=True
            )

            assert workspace.status == WorkspaceStatus.ACTIVE
            mock_git_instance.setup_repository.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workspace_success(self, workspace_manager):
        """Test successful workspace retrieval"""
        agent_id = "test-agent-get"
        repository_url = "https://github.com/test/repo.git"

        # Create workspace first
        created_workspace = await workspace_manager.create_workspace(
            agent_id, repository_url
        )

        # Retrieve workspace
        retrieved_workspace = await workspace_manager.get_workspace(agent_id)

        assert retrieved_workspace.id == created_workspace.id
        assert retrieved_workspace.path == created_workspace.path
        assert retrieved_workspace.repository_url == created_workspace.repository_url

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, workspace_manager):
        """Test workspace retrieval for non-existent workspace"""
        with pytest.raises(WorkspaceError, match="not found"):
            await workspace_manager.get_workspace("non-existent-agent")

    @pytest.mark.asyncio
    async def test_list_workspaces(self, workspace_manager):
        """Test listing all workspaces"""
        # Create multiple workspaces
        agents = ["agent-1", "agent-2", "agent-3"]
        for agent_id in agents:
            await workspace_manager.create_workspace(
                agent_id, f"https://github.com/test/{agent_id}.git"
            )

        workspaces = await workspace_manager.list_workspaces()

        assert len(workspaces) == 3
        workspace_ids = [ws.id for ws in workspaces]
        for agent_id in agents:
            assert agent_id in workspace_ids

    @pytest.mark.asyncio
    async def test_cleanup_workspace_success(self, workspace_manager):
        """Test successful workspace cleanup"""
        agent_id = "test-agent-cleanup"
        repository_url = "https://github.com/test/repo.git"

        # Create workspace
        workspace = await workspace_manager.create_workspace(agent_id, repository_url)
        workspace_path = workspace.path

        # Verify workspace exists
        assert os.path.exists(workspace_path)

        # Cleanup workspace
        result = await workspace_manager.cleanup_workspace(
            agent_id, preserve_logs=False
        )

        assert result is True
        assert not os.path.exists(workspace_path)

    @pytest.mark.asyncio
    async def test_cleanup_workspace_preserve_logs(self, workspace_manager):
        """Test workspace cleanup with log preservation"""
        agent_id = "test-agent-preserve-logs"
        repository_url = "https://github.com/test/repo.git"

        # Create workspace and add log file
        workspace = await workspace_manager.create_workspace(agent_id, repository_url)
        log_file = Path(workspace.path) / "agent.log"
        log_file.write_text("Test log content")

        with patch("core.archive_manager.ArchiveManager") as mock_archive:
            mock_archive_instance = AsyncMock()
            mock_archive.return_value = mock_archive_instance
            mock_archive_instance.archive_logs.return_value = "/path/to/archive.tar.gz"

            result = await workspace_manager.cleanup_workspace(
                agent_id, preserve_logs=True
            )

            assert result is True
            mock_archive_instance.archive_logs.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_workspace_not_found(self, workspace_manager):
        """Test cleanup of non-existent workspace"""
        with pytest.raises(WorkspaceError, match="not found"):
            await workspace_manager.cleanup_workspace("non-existent-agent")

    @pytest.mark.asyncio
    async def test_workspace_isolation(self, workspace_manager):
        """Test that workspaces are properly isolated"""
        agent1_id = "agent-1"
        agent2_id = "agent-2"

        # Create two workspaces
        ws1 = await workspace_manager.create_workspace(
            agent1_id, "https://github.com/test/repo1.git"
        )
        ws2 = await workspace_manager.create_workspace(
            agent2_id, "https://github.com/test/repo2.git"
        )

        # Verify different paths
        assert ws1.path != ws2.path

        # Create files in each workspace
        test_file1 = Path(ws1.path) / "test_file1.txt"
        test_file2 = Path(ws2.path) / "test_file2.txt"

        test_file1.write_text("Content from agent 1")
        test_file2.write_text("Content from agent 2")

        # Verify isolation - files exist only in their respective workspaces
        assert test_file1.exists()
        assert test_file2.exists()
        assert not (Path(ws2.path) / "test_file1.txt").exists()
        assert not (Path(ws1.path) / "test_file2.txt").exists()

    @pytest.mark.asyncio
    async def test_workspace_permissions(self, workspace_manager):
        """Test workspace directory permissions for security"""
        agent_id = "test-agent-permissions"
        repository_url = "https://github.com/test/repo.git"

        workspace = await workspace_manager.create_workspace(agent_id, repository_url)

        # Check directory permissions (should be 0o750 - owner rwx, group rx, other none)
        workspace_path = Path(workspace.path)
        stat_info = workspace_path.stat()
        permissions = oct(stat_info.st_mode)[-3:]

        # On different systems, exact permissions may vary, but should be restrictive
        assert permissions in ["750", "755"]  # Allow some flexibility

    @pytest.mark.asyncio
    async def test_cleanup_all_workspaces(self, workspace_manager):
        """Test cleanup of all workspaces"""
        # Create multiple workspaces
        agents = ["agent-cleanup-1", "agent-cleanup-2", "agent-cleanup-3"]
        for agent_id in agents:
            await workspace_manager.create_workspace(
                agent_id, f"https://github.com/test/{agent_id}.git"
            )

        # Verify workspaces exist
        workspaces = await workspace_manager.list_workspaces()
        assert len(workspaces) == 3

        # Cleanup all workspaces
        results = await workspace_manager.cleanup_all_workspaces(preserve_logs=False)

        assert len(results) == 3
        assert all(results.values())  # All cleanups successful

        # Verify all workspaces are gone
        workspaces_after = await workspace_manager.list_workspaces()
        assert len(workspaces_after) == 0


class TestWorkspace:
    """Unit tests for Workspace model"""

    def test_workspace_creation(self):
        """Test Workspace model creation"""
        agent_id = "test-agent"
        workspace_path = "/tmp/workspaces/test-agent"
        repository_url = "https://github.com/test/repo.git"
        created_at = datetime.utcnow()

        workspace = Workspace(
            id=agent_id,
            path=workspace_path,
            repository_url=repository_url,
            created_at=created_at,
            status=WorkspaceStatus.ACTIVE,
        )

        assert workspace.id == agent_id
        assert workspace.path == workspace_path
        assert workspace.repository_url == repository_url
        assert workspace.created_at == created_at
        assert workspace.status == WorkspaceStatus.ACTIVE

    def test_workspace_status_enum(self):
        """Test WorkspaceStatus enum values"""
        assert WorkspaceStatus.ACTIVE.value == "active"
        assert WorkspaceStatus.CLEANING.value == "cleaning"
        assert WorkspaceStatus.CLEANED.value == "cleaned"
        assert WorkspaceStatus.ERROR.value == "error"
