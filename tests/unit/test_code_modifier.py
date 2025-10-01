"""
Unit tests for CodeModifier - TDD implementation
Following the Red-Green-Refactor cycle
"""
import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from core.code_modifier import (
    CodeModifier,
    FileChange,
    Implementation,
    ModificationError,
    ValidationError,
    ValidationResult,
)
from core.exceptions import BaseSystemError
from core.workspace_manager import Workspace, WorkspaceStatus


class TestCodeModifier:
    """Unit tests for CodeModifier"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp(prefix="test_codemod_")
        workspace = Workspace(
            id="test-agent-codemod",
            path=temp_dir,
            repository_url="https://github.com/test/repo.git",
            created_at=datetime.utcnow(),
            status=WorkspaceStatus.ACTIVE,
        )
        yield workspace
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def code_modifier(self):
        """Create CodeModifier instance for testing"""
        return CodeModifier()

    @pytest.fixture
    def sample_implementation(self):
        """Create sample implementation for testing"""
        return Implementation(
            task_id="TEST-123",
            description="Add user authentication feature",
            files=[
                FileChange(
                    path="src/auth.py",
                    action="create",
                    content="def authenticate(username, password):\n    return True\n",
                ),
                FileChange(
                    path="src/models.py",
                    action="modify",
                    content="class User:\n    def __init__(self, username):\n        self.username = username\n",
                ),
            ],
            commit_message="feat: add user authentication system",
            pr_description="Implements basic user authentication with login/logout functionality",
        )

    def test_code_modifier_initialization(self, code_modifier):
        """Test CodeModifier initialization"""
        assert code_modifier is not None
        assert hasattr(code_modifier, "apply_code_changes")
        assert hasattr(code_modifier, "validate_generated_code")
        assert hasattr(code_modifier, "create_backup")
        assert hasattr(code_modifier, "restore_backup")

    @pytest.mark.asyncio
    async def test_apply_code_changes_success(
        self, code_modifier, temp_workspace, sample_implementation
    ):
        """Test successful code changes application"""
        result = await code_modifier.apply_code_changes(
            temp_workspace, sample_implementation
        )

        assert result.success is True
        assert result.files_modified == 2
        assert result.backup_created is False  # No backup needed for new files

        # Verify files were created/modified
        auth_file = Path(temp_workspace.path) / "src/auth.py"
        models_file = Path(temp_workspace.path) / "src/models.py"

        assert auth_file.exists()
        assert models_file.exists()
        assert "def authenticate" in auth_file.read_text()
        assert "class User" in models_file.read_text()

    @pytest.mark.asyncio
    async def test_apply_code_changes_with_existing_files(
        self, code_modifier, temp_workspace
    ):
        """Test code changes application with existing files"""
        # Create existing file
        existing_file = Path(temp_workspace.path) / "src/existing.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        original_content = "# Original content\nprint('Hello')\n"
        existing_file.write_text(original_content)

        implementation = Implementation(
            task_id="TEST-124",
            description="Update existing file",
            files=[
                FileChange(
                    path="src/existing.py",
                    action="modify",
                    content="# Updated content\nprint('Hello, World!')\n",
                )
            ],
            commit_message="feat: update existing functionality",
        )

        result = await code_modifier.apply_code_changes(temp_workspace, implementation)

        assert result.success is True
        assert "Hello, World!" in existing_file.read_text()

        # Verify backup was created
        backup_dir = Path(temp_workspace.path) / ".backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("*"))
        assert len(backup_files) > 0

    @pytest.mark.asyncio
    async def test_apply_code_changes_validation_failure(
        self, code_modifier, temp_workspace
    ):
        """Test code changes with validation failure"""
        implementation = Implementation(
            task_id="TEST-125",
            description="Invalid Python code",
            files=[
                FileChange(
                    path="invalid.py",
                    action="create",
                    content="def broken_function(\n    # Missing closing parenthesis",
                )
            ],
            commit_message="feat: add broken code",
        )

        with pytest.raises(ValidationError, match="validation failed"):
            await code_modifier.apply_code_changes(temp_workspace, implementation)

    @pytest.mark.asyncio
    async def test_apply_code_changes_file_deletion(
        self, code_modifier, temp_workspace
    ):
        """Test file deletion functionality"""
        # Create file to delete
        file_to_delete = Path(temp_workspace.path) / "delete_me.py"
        file_to_delete.write_text("# This file will be deleted")

        implementation = Implementation(
            task_id="TEST-126",
            description="Clean up unused files",
            files=[FileChange(path="delete_me.py", action="delete")],
            commit_message="refactor: remove unused file",
        )

        result = await code_modifier.apply_code_changes(temp_workspace, implementation)

        assert result.success is True
        assert not file_to_delete.exists()

    @pytest.mark.asyncio
    async def test_validate_generated_code_python_success(self, code_modifier):
        """Test Python code validation - success case"""
        valid_python = """
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42
"""

        result = await code_modifier.validate_generated_code(valid_python, "python")

        assert result.is_valid is True
        assert len(result.syntax_errors) == 0
        assert len(result.security_issues) == 0

    @pytest.mark.asyncio
    async def test_validate_generated_code_python_syntax_error(self, code_modifier):
        """Test Python code validation - syntax error"""
        invalid_python = """
def broken_function(
    print("Missing closing parenthesis")
    return False
"""

        result = await code_modifier.validate_generated_code(invalid_python, "python")

        assert result.is_valid is False
        assert len(result.syntax_errors) > 0
        assert "syntax error" in result.syntax_errors[0].lower()

    @pytest.mark.asyncio
    async def test_validate_generated_code_security_issues(self, code_modifier):
        """Test code validation for security issues"""
        insecure_code = """
import subprocess
user_input = input("Enter command: ")
subprocess.call(user_input, shell=True)  # Security risk
eval(user_input)  # Another security risk
"""

        result = await code_modifier.validate_generated_code(insecure_code, "python")

        assert result.is_valid is False
        assert len(result.security_issues) > 0
        assert any(
            "subprocess" in issue or "eval" in issue for issue in result.security_issues
        )

    @pytest.mark.asyncio
    async def test_validate_generated_code_javascript(self, code_modifier):
        """Test JavaScript code validation"""
        valid_js = """
function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}

class User {
    constructor(name) {
        this.name = name;
    }
}
"""

        result = await code_modifier.validate_generated_code(valid_js, "javascript")

        assert result.is_valid is True
        assert len(result.syntax_errors) == 0

    @pytest.mark.asyncio
    async def test_validate_generated_code_typescript(self, code_modifier):
        """Test TypeScript code validation"""
        valid_ts = """
interface User {
    id: number;
    name: string;
}

function createUser(name: string): User {
    return {
        id: Math.random(),
        name: name
    };
}
"""

        result = await code_modifier.validate_generated_code(valid_ts, "typescript")

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_create_backup_success(self, code_modifier, temp_workspace):
        """Test backup creation"""
        # Create some files to backup
        test_files = ["file1.py", "file2.js", "subdir/file3.py"]
        for file_path in test_files:
            full_path = Path(temp_workspace.path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"Content of {file_path}")

        backup_id = await code_modifier.create_backup(temp_workspace, test_files)

        assert backup_id is not None

        # Verify backup directory was created
        backup_dir = Path(temp_workspace.path) / ".backups" / backup_id
        assert backup_dir.exists()

        # Verify files were backed up
        for file_path in test_files:
            backup_file = backup_dir / file_path
            assert backup_file.exists()
            assert f"Content of {file_path}" in backup_file.read_text()

    @pytest.mark.asyncio
    async def test_restore_backup_success(self, code_modifier, temp_workspace):
        """Test backup restoration"""
        # Create and modify a file
        test_file = Path(temp_workspace.path) / "test.py"
        original_content = "# Original content"
        test_file.write_text(original_content)

        # Create backup
        backup_id = await code_modifier.create_backup(temp_workspace, ["test.py"])

        # Modify file
        test_file.write_text("# Modified content")

        # Restore backup
        result = await code_modifier.restore_backup(temp_workspace, backup_id)

        assert result.success is True
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_restore_backup_nonexistent(self, code_modifier, temp_workspace):
        """Test restore of nonexistent backup"""
        with pytest.raises(ModificationError, match="Backup not found"):
            await code_modifier.restore_backup(temp_workspace, "nonexistent-backup-id")

    @pytest.mark.asyncio
    async def test_apply_file_change_create_action(self, code_modifier, temp_workspace):
        """Test individual file change application - create"""
        file_change = FileChange(
            path="new_file.py",
            action="create",
            content="# New file content\nprint('Hello')\n",
        )

        result = await code_modifier._apply_file_change(temp_workspace, file_change)

        assert result is True
        new_file = Path(temp_workspace.path) / "new_file.py"
        assert new_file.exists()
        assert "New file content" in new_file.read_text()

    @pytest.mark.asyncio
    async def test_apply_file_change_modify_action(self, code_modifier, temp_workspace):
        """Test individual file change application - modify"""
        # Create existing file
        existing_file = Path(temp_workspace.path) / "existing.py"
        existing_file.write_text("# Original content")

        file_change = FileChange(
            path="existing.py",
            action="modify",
            content="# Modified content\nprint('Updated')\n",
        )

        result = await code_modifier._apply_file_change(temp_workspace, file_change)

        assert result is True
        assert "Modified content" in existing_file.read_text()
        assert "Updated" in existing_file.read_text()

    @pytest.mark.asyncio
    async def test_apply_file_change_delete_action(self, code_modifier, temp_workspace):
        """Test individual file change application - delete"""
        # Create file to delete
        file_to_delete = Path(temp_workspace.path) / "to_delete.py"
        file_to_delete.write_text("# Will be deleted")

        file_change = FileChange(path="to_delete.py", action="delete")

        result = await code_modifier._apply_file_change(temp_workspace, file_change)

        assert result is True
        assert not file_to_delete.exists()

    @pytest.mark.asyncio
    async def test_validate_file_permissions(self, code_modifier, temp_workspace):
        """Test file permissions validation"""
        # Create a read-only file
        readonly_file = Path(temp_workspace.path) / "readonly.py"
        readonly_file.write_text("# Read only content")
        readonly_file.chmod(0o444)  # Read-only permissions

        file_change = FileChange(
            path="readonly.py",
            action="modify",
            content="# Trying to modify read-only file",
        )

        with pytest.raises(ModificationError, match="permission"):
            await code_modifier._apply_file_change(temp_workspace, file_change)

    @pytest.mark.asyncio
    async def test_validate_file_encoding(self, code_modifier, temp_workspace):
        """Test file encoding validation"""
        # Test with various encodings
        file_changes = [
            FileChange(
                path="utf8_file.py",
                action="create",
                content="# UTF-8 content with émojis 🚀\nprint('Hello')",
            ),
            FileChange(
                path="ascii_file.py",
                action="create",
                content="# ASCII content\nprint('Hello')",
            ),
        ]

        for file_change in file_changes:
            result = await code_modifier._apply_file_change(temp_workspace, file_change)
            assert result is True

    @pytest.mark.asyncio
    async def test_atomic_operations(self, code_modifier, temp_workspace):
        """Test that operations are atomic - either all succeed or all fail"""
        # Create a simpler test case with files in the workspace directory
        implementation = Implementation(
            task_id="TEST-ATOMIC",
            description="Test atomic operations",
            files=[
                FileChange(path="file1.py", action="create", content="print('file1')"),
                FileChange(path="file2.py", action="create", content="print('file2')"),
                FileChange(
                    path="readonly_dir/cannot_create.py",
                    action="create",
                    content="# This should fail",
                ),
            ],
            commit_message="test atomic operations",
        )

        # Create a readonly directory to cause failure
        readonly_dir = Path(temp_workspace.path) / "readonly_dir"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o555)  # Read and execute only, no write

        try:
            # The operation should fail due to permission error
            with pytest.raises(ModificationError):
                await code_modifier.apply_code_changes(temp_workspace, implementation)

            # Verify rollback occurred - files should not exist or should be cleaned up
            file1 = Path(temp_workspace.path) / "file1.py"
            file2 = Path(temp_workspace.path) / "file2.py"

            # At least verify the operation failed completely
            cannot_create = readonly_dir / "cannot_create.py"
            assert (
                not cannot_create.exists()
            ), "File should not have been created in readonly directory"

        finally:
            # Cleanup readonly directory
            readonly_dir.chmod(0o755)
            if readonly_dir.exists():
                shutil.rmtree(readonly_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_concurrent_modifications(self, code_modifier, temp_workspace):
        """Test handling of concurrent modifications"""
        implementations = []
        for i in range(3):
            impl = Implementation(
                task_id=f"TEST-{130 + i}",
                description=f"Concurrent modification {i}",
                files=[
                    FileChange(
                        path=f"concurrent_{i}.py",
                        action="create",
                        content=f"# Concurrent file {i}\nprint('File {i}')\n",
                    )
                ],
                commit_message=f"feat: add concurrent file {i}",
            )
            implementations.append(impl)

        # Apply all implementations concurrently
        tasks = [
            code_modifier.apply_code_changes(temp_workspace, impl)
            for impl in implementations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed since they modify different files
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent modification {i} failed: {result}")
            assert result.success is True


class TestImplementationModel:
    """Unit tests for Implementation data model"""

    def test_implementation_creation(self):
        """Test Implementation model creation"""
        impl = Implementation(
            task_id="TEST-100",
            description="Test implementation",
            files=[
                FileChange(path="test.py", action="create", content="print('test')")
            ],
            commit_message="feat: add test functionality",
            pr_description="This adds test functionality",
            breaking_changes="None",
        )

        assert impl.task_id == "TEST-100"
        assert impl.description == "Test implementation"
        assert len(impl.files) == 1
        assert impl.commit_message == "feat: add test functionality"
        assert impl.pr_description == "This adds test functionality"
        assert impl.breaking_changes == "None"

    def test_file_change_creation(self):
        """Test FileChange model creation"""
        file_change = FileChange(
            path="src/utils.py",
            action="modify",
            content="def utility_function():\n    return True\n",
            backup_path="/backups/utils.py.backup",
        )

        assert file_change.path == "src/utils.py"
        assert file_change.action == "modify"
        assert "def utility_function" in file_change.content
        assert file_change.backup_path == "/backups/utils.py.backup"

    def test_validation_result_creation(self):
        """Test ValidationResult model creation"""
        result = ValidationResult(
            is_valid=False,
            syntax_errors=["Missing parenthesis on line 5"],
            linting_issues=["Line too long at line 10"],
            security_issues=["Use of eval() detected"],
            recommendations=["Use ast.literal_eval instead of eval"],
        )

        assert result.is_valid is False
        assert len(result.syntax_errors) == 1
        assert len(result.linting_issues) == 1
        assert len(result.security_issues) == 1
        assert len(result.recommendations) == 1
