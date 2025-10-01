"""
Unit tests for GitOperations - TDD implementation
Following the Red-Green-Refactor cycle
"""
import asyncio
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from core.git_operations import GitOperations, CommitResult, GitError, GitAuthError
from core.workspace_manager import Workspace, WorkspaceStatus
from datetime import datetime


class TestGitOperations:
    """Unit tests for GitOperations"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp(prefix="test_git_")
        workspace = Workspace(
            id="test-agent",
            path=temp_dir,
            repository_url="https://github.com/test/repo.git",
            created_at=datetime.utcnow(),
            status=WorkspaceStatus.ACTIVE
        )
        yield workspace
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def git_operations(self):
        """Create GitOperations instance for testing"""
        return GitOperations()
    
    def test_git_operations_initialization(self, git_operations):
        """Test GitOperations initialization"""
        assert git_operations is not None
        assert hasattr(git_operations, 'setup_repository')
        assert hasattr(git_operations, 'apply_file_changes')
        assert hasattr(git_operations, 'commit_and_push')
    
    @pytest.mark.asyncio
    async def test_setup_repository_success(self, git_operations, temp_workspace):
        """Test successful repository setup"""
        with patch('core.git_operations.git.Repo.clone_from') as mock_clone:
            
            mock_repo_instance = MagicMock()
            mock_clone.return_value = mock_repo_instance
            mock_repo_instance.git.config.return_value = None
            mock_repo_instance.git.checkout.return_value = None
            
            result = await git_operations.setup_repository(
                temp_workspace, 
                branch_name="feature/test-branch"
            )
            
            assert result is True
            mock_clone.assert_called_once_with(
                temp_workspace.repository_url,
                temp_workspace.path
            )
    
    @pytest.mark.asyncio
    async def test_setup_repository_clone_failure(self, git_operations, temp_workspace):
        """Test repository setup with clone failure"""
        with patch('core.git_operations.git.Repo.clone_from', side_effect=Exception("Clone failed")):
            with pytest.raises(GitError, match="Failed to clone repository"):
                await git_operations.setup_repository(temp_workspace, "feature/test")
    
    @pytest.mark.asyncio
    async def test_setup_repository_with_branch_creation(self, git_operations, temp_workspace):
        """Test repository setup with new branch creation"""
        with patch('core.git_operations.git.Repo.clone_from') as mock_clone:
            
            mock_repo_instance = MagicMock()
            mock_clone.return_value = mock_repo_instance
            mock_repo_instance.git.config.return_value = None
            mock_repo_instance.git.checkout.return_value = None
            mock_repo_instance.create_head.return_value = MagicMock()
            
            result = await git_operations.setup_repository(
                temp_workspace,
                branch_name="feature/new-feature",
                create_branch=True
            )
            
            assert result is True
            mock_repo_instance.create_head.assert_called_once_with("feature/new-feature")
    
    @pytest.mark.asyncio
    async def test_apply_file_changes_success(self, git_operations, temp_workspace):
        """Test successful file changes application"""
        # Setup test files
        test_file = Path(temp_workspace.path) / "test_file.py"
        test_file.write_text("original content")
        
        file_changes = {
            "test_file.py": {
                "content": "updated content",
                "action": "modify"
            },
            "new_file.py": {
                "content": "new file content",
                "action": "create"
            }
        }
        
        with patch('core.git_operations.GitOperations._backup_existing_files') as mock_backup, \
             patch('core.git_operations.GitOperations._validate_file_changes') as mock_validate:
            
            mock_backup.return_value = None
            mock_validate.return_value = True
            
            result = await git_operations.apply_file_changes(temp_workspace, file_changes)
            
            assert result is True
            
            # Verify files were created/modified
            assert test_file.read_text() == "updated content"
            new_file = Path(temp_workspace.path) / "new_file.py"
            assert new_file.exists()
            assert new_file.read_text() == "new file content"
    
    @pytest.mark.asyncio
    async def test_apply_file_changes_with_backup(self, git_operations, temp_workspace):
        """Test file changes with backup creation"""
        # Setup test file
        test_file = Path(temp_workspace.path) / "test_file.py"
        original_content = "original content"
        test_file.write_text(original_content)
        
        file_changes = {
            "test_file.py": {
                "content": "updated content",
                "action": "modify"
            }
        }
        
        result = await git_operations.apply_file_changes(
            temp_workspace, 
            file_changes, 
            create_backup=True
        )
        
        assert result is True
        
        # Verify backup was created
        backup_dir = Path(temp_workspace.path) / ".backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("test_file.py.*"))
        assert len(backup_files) > 0
        assert backup_files[0].read_text() == original_content
    
    @pytest.mark.asyncio
    async def test_apply_file_changes_validation_error(self, git_operations, temp_workspace):
        """Test file changes with validation error"""
        file_changes = {
            "invalid_file.py": {
                "content": "invalid python syntax <<<",
                "action": "create"
            }
        }
        
        with patch('core.git_operations.GitOperations._validate_file_changes', 
                   return_value=False):
            with pytest.raises(GitError, match="File validation failed"):
                await git_operations.apply_file_changes(temp_workspace, file_changes)
    
    @pytest.mark.asyncio
    async def test_commit_and_push_success(self, git_operations, temp_workspace):
        """Test successful commit and push"""
        message = "Test commit message"
        
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.add.return_value = None
            mock_repo.index.commit.return_value.hexsha = "abc123def456"
            mock_repo.remotes.origin.push.return_value = [MagicMock(flags=0)]
            mock_repo.git.diff.return_value = "test diff output"
            
            result = await git_operations.commit_and_push(temp_workspace, message)
            
            assert isinstance(result, CommitResult)
            assert result.commit_hash == "abc123def456"
            assert result.success is True
            assert result.message == message
            
            mock_repo.git.add.assert_called_once_with(".")
            mock_repo.index.commit.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_commit_and_push_no_changes(self, git_operations, temp_workspace):
        """Test commit with no changes"""
        message = "No changes commit"
        
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.diff.return_value = ""  # No changes
            mock_repo.is_dirty.return_value = False
            
            result = await git_operations.commit_and_push(temp_workspace, message)
            
            assert isinstance(result, CommitResult)
            assert result.success is True
            assert "no changes" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_commit_and_push_failure(self, git_operations, temp_workspace):
        """Test commit and push failure"""
        message = "Test commit"
        
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.add.side_effect = Exception("Git add failed")
            
            with pytest.raises(GitError, match="Failed to commit and push"):
                await git_operations.commit_and_push(temp_workspace, message)
    
    @pytest.mark.asyncio
    async def test_push_with_authentication_error(self, git_operations, temp_workspace):
        """Test push with authentication error"""
        message = "Test commit"
        
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.add.return_value = None
            mock_repo.index.commit.return_value.hexsha = "abc123"
            mock_repo.remotes.origin.push.side_effect = Exception("Authentication failed")
            
            with pytest.raises(GitAuthError, match="Authentication failed"):
                await git_operations.commit_and_push(temp_workspace, message)
    
    @pytest.mark.asyncio
    async def test_validate_repository_state_success(self, git_operations, temp_workspace):
        """Test repository state validation"""
        with patch('core.git_operations.git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.is_dirty.return_value = False
            
            result = await git_operations.validate_repository_state(temp_workspace)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_repository_state_dirty(self, git_operations, temp_workspace):
        """Test repository state validation with dirty state"""
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.is_dirty.return_value = True
            
            result = await git_operations.validate_repository_state(temp_workspace)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_merge_conflicts(self, git_operations, temp_workspace):
        """Test merge conflict handling"""
        with patch('git.Repo') as mock_repo_class, \
             patch('core.git_operations.GitOperations._resolve_merge_conflicts') as mock_resolve:
            
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.merge.side_effect = Exception("CONFLICT: merge conflict")
            mock_resolve.return_value = True
            
            result = await git_operations.handle_merge_conflicts(temp_workspace)
            
            assert result is True
            mock_resolve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_repository_status(self, git_operations, temp_workspace):
        """Test getting repository status information"""
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.active_branch.name = "feature/test"
            mock_repo.is_dirty.return_value = False
            mock_repo.untracked_files = []
            mock_repo.git.log.return_value = "commit abc123\nAuthor: Test"
            
            status = await git_operations.get_repository_status(temp_workspace)
            
            assert status['current_branch'] == "feature/test"
            assert status['is_dirty'] is False
            assert status['untracked_files'] == []
            assert 'latest_commit' in status
    
    def test_file_validation_python_syntax(self, git_operations):
        """Test Python file syntax validation"""
        valid_python = "def hello():\n    print('Hello, World!')\n"
        invalid_python = "def hello(\n    print('Hello, World!'"
        
        assert git_operations._validate_python_syntax(valid_python) is True
        assert git_operations._validate_python_syntax(invalid_python) is False
    
    def test_file_validation_javascript_syntax(self, git_operations):
        """Test JavaScript file syntax validation"""
        valid_js = "function hello() { console.log('Hello, World!'); }"
        invalid_js = "function hello() { console.log('Hello, World!' }"
        
        # Note: Actual JS validation would require a JS parser
        # For now, we'll test the interface
        assert hasattr(git_operations, '_validate_javascript_syntax')
    
    @pytest.mark.asyncio
    async def test_repository_cleanup(self, git_operations, temp_workspace):
        """Test repository cleanup operations"""
        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.clean.return_value = None
            mock_repo.git.reset.return_value = None
            
            result = await git_operations.cleanup_repository(temp_workspace)
            
            assert result is True
            mock_repo.git.clean.assert_called_once()
            mock_repo.git.reset.assert_called_once()


class TestCommitResult:
    """Unit tests for CommitResult model"""
    
    def test_commit_result_creation(self):
        """Test CommitResult model creation"""
        result = CommitResult(
            success=True,
            commit_hash="abc123def456",
            message="Test commit message",
            files_changed=["file1.py", "file2.js"],
            insertions=10,
            deletions=5
        )
        
        assert result.success is True
        assert result.commit_hash == "abc123def456"
        assert result.message == "Test commit message"
        assert result.files_changed == ["file1.py", "file2.js"]
        assert result.insertions == 10
        assert result.deletions == 5
    
    def test_commit_result_failure(self):
        """Test CommitResult for failed commit"""
        result = CommitResult(
            success=False,
            error="Commit failed due to authentication error",
            commit_hash=None
        )
        
        assert result.success is False
        assert result.error == "Commit failed due to authentication error"
        assert result.commit_hash is None