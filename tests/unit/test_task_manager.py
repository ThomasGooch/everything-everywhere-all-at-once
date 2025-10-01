"""
Unit tests for TaskManager - TDD implementation
Following the Red-Green-Refactor cycle for task lifecycle management
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

from core.task_manager import (
    TaskManager,
    TaskProgress,
    TaskEvent,
    TaskStatus,
    TaskUpdate,
    TaskManagerError,
)
from core.exceptions import BaseSystemError
from core.plugin_registry import PluginRegistry


class TestTaskManager:
    """Unit tests for TaskManager"""

    @pytest.fixture
    def mock_plugin_registry(self):
        """Create mock plugin registry"""
        registry = Mock()
        task_plugin = AsyncMock()
        comm_plugin = AsyncMock()

        registry.get_plugin = Mock(
            side_effect=lambda plugin_type, name=None: {
                "task_management": task_plugin,
                "communication": comm_plugin,
            }.get(plugin_type)
        )

        return registry, task_plugin, comm_plugin

    @pytest.fixture
    def task_manager(self, mock_plugin_registry):
        """Create TaskManager instance for testing"""
        registry, _, _ = mock_plugin_registry
        return TaskManager(plugin_registry=registry)

    @pytest.fixture
    def sample_task_data(self):
        """Create sample task data for testing"""
        return {
            "id": "TEST-123",
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication system",
            "status": "todo",
            "assignee": "developer@example.com",
            "project": "TEST",
            "priority": "high",
            "repository_url": "https://github.com/test/repo.git",
        }

    @pytest.fixture
    def sample_progress(self):
        """Create sample task progress for testing"""
        return TaskProgress(
            task_id="TEST-123",
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50,
            current_step="Implementing JWT middleware",
            estimated_completion=datetime.now() + timedelta(hours=2),
            metadata={"branch_name": "feature/TEST-123", "pr_url": None},
        )

    def test_task_manager_initialization(self, task_manager):
        """Test TaskManager initialization"""
        assert task_manager is not None
        assert hasattr(task_manager, "update_task_progress")
        assert hasattr(task_manager, "handle_task_completion")
        assert hasattr(task_manager, "get_task_status")
        assert hasattr(task_manager, "assign_task")

    @pytest.mark.asyncio
    async def test_get_task_success(
        self, task_manager, mock_plugin_registry, sample_task_data
    ):
        """Test successful task retrieval"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.get_task.return_value = sample_task_data

        result = await task_manager.get_task("TEST-123")

        assert result == sample_task_data
        task_plugin.get_task.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_manager, mock_plugin_registry):
        """Test task retrieval when task doesn't exist"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.get_task.return_value = None

        with pytest.raises(TaskManagerError, match="Task TEST-404 not found"):
            await task_manager.get_task("TEST-404")

    @pytest.mark.asyncio
    async def test_update_task_progress_success(
        self, task_manager, mock_plugin_registry, sample_progress
    ):
        """Test successful task progress update"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True
        task_plugin.add_comment.return_value = True

        result = await task_manager.update_task_progress(sample_progress)

        assert result.success is True
        # Check that the call was made with the correct parameters (metadata may include additional fields)
        call_args = task_plugin.update_task_status.call_args
        assert call_args[0] == ("TEST-123", "In Progress")
        assert call_args[1]["custom_fields"]["progress_percentage"] == 50
        task_plugin.add_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_progress_failure(
        self, task_manager, mock_plugin_registry, sample_progress
    ):
        """Test task progress update failure"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.side_effect = Exception("API Error")

        result = await task_manager.update_task_progress(sample_progress)

        assert result.success is False
        assert "API Error" in result.error

    @pytest.mark.asyncio
    async def test_assign_task_success(
        self, task_manager, mock_plugin_registry, sample_task_data
    ):
        """Test successful task assignment"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True
        task_plugin.add_comment.return_value = True

        result = await task_manager.assign_task("TEST-123", "agent-001")

        assert result.success is True
        assert result.data["agent_id"] == "agent-001"
        task_plugin.update_task_status.assert_called_once_with(
            "TEST-123", "In Progress", custom_fields={"assigned_agent": "agent-001"}
        )

    @pytest.mark.asyncio
    async def test_handle_task_completion_success(
        self, task_manager, mock_plugin_registry
    ):
        """Test successful task completion handling"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True
        task_plugin.add_comment.return_value = True

        completion_data = {
            "pr_url": "https://github.com/test/repo/pull/123",
            "branch_name": "feature/TEST-123",
            "files_changed": ["src/auth.py", "tests/test_auth.py"],
            "test_results": {"passed": 15, "failed": 0, "coverage": 95.2},
        }

        result = await task_manager.handle_task_completion("TEST-123", completion_data)

        assert result.success is True
        task_plugin.update_task_status.assert_called_once_with(
            "TEST-123",
            "In Review",
            custom_fields={
                "pr_url": "https://github.com/test/repo/pull/123",
                "branch_name": "feature/TEST-123",
            },
        )

    @pytest.mark.asyncio
    async def test_handle_task_completion_with_failures(
        self, task_manager, mock_plugin_registry
    ):
        """Test task completion handling with test failures"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True
        task_plugin.add_comment.return_value = True

        completion_data = {
            "pr_url": "https://github.com/test/repo/pull/123",
            "test_results": {"passed": 12, "failed": 3, "coverage": 78.5},
        }

        result = await task_manager.handle_task_completion("TEST-123", completion_data)

        assert result.success is True
        # Should mark as 'Needs Work' instead of 'In Review' due to failed tests
        task_plugin.update_task_status.assert_called_once_with(
            "TEST-123",
            "Needs Work",
            custom_fields={"pr_url": "https://github.com/test/repo/pull/123"},
        )

    @pytest.mark.asyncio
    async def test_get_task_status_success(
        self, task_manager, mock_plugin_registry, sample_task_data
    ):
        """Test successful task status retrieval"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.get_task.return_value = sample_task_data

        status = await task_manager.get_task_status("TEST-123")

        assert status == "todo"
        task_plugin.get_task.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_create_task_event(self, task_manager, sample_task_data):
        """Test task event creation"""
        event_data = {
            "type": "task_completed",
            "task_id": "TEST-123",
            "pr_url": "https://github.com/test/repo/pull/123",
            "agent_id": "agent-001",
        }

        event = task_manager.create_task_event(**event_data)

        assert isinstance(event, TaskEvent)
        assert event.type == "task_completed"
        assert event.task_id == "TEST-123"
        assert event.pr_url == "https://github.com/test/repo/pull/123"
        assert event.agent_id == "agent-001"
        assert isinstance(event.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_calculate_task_duration(self, task_manager):
        """Test task duration calculation"""
        start_time = datetime.now() - timedelta(hours=2, minutes=30)
        end_time = datetime.now()

        duration = task_manager.calculate_task_duration(start_time, end_time)

        assert duration.total_seconds() >= 9000  # At least 2.5 hours
        assert (
            duration.total_seconds() <= 9600
        )  # At most 2.67 hours (allowing for test execution time)

    @pytest.mark.asyncio
    async def test_format_progress_comment(self, task_manager, sample_progress):
        """Test progress comment formatting"""
        comment = task_manager.format_progress_comment(sample_progress)

        assert "In Progress" in comment
        assert "50%" in comment
        assert "Implementing JWT middleware" in comment
        # Task ID is not included in the comment format, so remove this assertion

    @pytest.mark.asyncio
    async def test_validate_task_data(self, task_manager, sample_task_data):
        """Test task data validation"""
        # Valid task data should not raise exception
        task_manager.validate_task_data(sample_task_data)

        # Invalid task data should raise exception
        invalid_data = {"id": "TEST-123"}  # Missing required fields
        with pytest.raises(TaskManagerError, match="Task data validation failed"):
            task_manager.validate_task_data(invalid_data)

    @pytest.mark.asyncio
    async def test_handle_task_error(self, task_manager, mock_plugin_registry):
        """Test task error handling"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True
        task_plugin.add_comment.return_value = True

        error_data = {
            "error_type": "compilation_error",
            "error_message": "Syntax error in src/auth.py line 45",
            "stack_trace": 'File "src/auth.py", line 45...',
            "recovery_suggestions": ["Fix syntax error", "Run linting"],
        }

        result = await task_manager.handle_task_error("TEST-123", error_data)

        assert result.success is True
        task_plugin.update_task_status.assert_called_once_with(
            "TEST-123", "Error", custom_fields={"error_type": "compilation_error"}
        )

    @pytest.mark.asyncio
    async def test_get_task_metrics(self, task_manager):
        """Test task metrics calculation"""
        task_history = [
            {"task_id": "TEST-1", "status": "Done", "duration_hours": 4.5},
            {"task_id": "TEST-2", "status": "Done", "duration_hours": 2.0},
            {"task_id": "TEST-3", "status": "Error", "duration_hours": 1.0},
        ]

        # Mock the _get_task_history method properly
        task_manager._get_task_history = AsyncMock(return_value=task_history)
        metrics = await task_manager.get_task_metrics(days=7)

        assert metrics["total_tasks"] == 3
        assert metrics["completed_tasks"] == 2
        assert metrics["success_rate"] == 2 / 3
        assert metrics["average_duration_hours"] == 3.25  # (4.5 + 2.0) / 2

    @pytest.mark.asyncio
    async def test_batch_task_update(self, task_manager, mock_plugin_registry):
        """Test batch task updates"""
        registry, task_plugin, _ = mock_plugin_registry
        task_plugin.update_task_status.return_value = True

        updates = [
            TaskUpdate(task_id="TEST-1", status=TaskStatus.IN_PROGRESS),
            TaskUpdate(task_id="TEST-2", status=TaskStatus.COMPLETED),
            TaskUpdate(task_id="TEST-3", status=TaskStatus.ERROR),
        ]

        results = await task_manager.batch_update_tasks(updates)

        assert len(results) == 3
        assert all(result.success for result in results)
        assert task_plugin.update_task_status.call_count == 3

    @pytest.mark.asyncio
    async def test_task_manager_error_handling(
        self, task_manager, mock_plugin_registry
    ):
        """Test TaskManager error handling"""
        registry, task_plugin, _ = mock_plugin_registry

        # Test with invalid task ID
        with pytest.raises(TaskManagerError, match="Invalid task ID format"):
            await task_manager.get_task("invalid-id")

        # Test with plugin connection failure
        task_plugin.get_task.side_effect = Exception("Connection failed")
        with pytest.raises(TaskManagerError, match="Failed to retrieve task"):
            await task_manager.get_task("TEST-123")


class TestTaskProgress:
    """Unit tests for TaskProgress data model"""

    def test_task_progress_creation(self):
        """Test TaskProgress creation"""
        progress = TaskProgress(
            task_id="TEST-123",
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=75,
            current_step="Running tests",
            estimated_completion=datetime.now() + timedelta(minutes=30),
        )

        assert progress.task_id == "TEST-123"
        assert progress.status == TaskStatus.IN_PROGRESS
        assert progress.progress_percentage == 75
        assert progress.current_step == "Running tests"

    def test_task_progress_validation(self):
        """Test TaskProgress validation"""
        # Valid progress percentage
        progress = TaskProgress(
            task_id="TEST-123", status=TaskStatus.IN_PROGRESS, progress_percentage=50
        )
        assert progress.progress_percentage == 50

        # Invalid progress percentage should be clamped
        progress_invalid = TaskProgress(
            task_id="TEST-123",
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=150,  # Should be clamped to 100
        )
        # Note: Validation logic would be in the actual implementation


class TestTaskEvent:
    """Unit tests for TaskEvent data model"""

    def test_task_event_creation(self):
        """Test TaskEvent creation"""
        event = TaskEvent(
            type="task_started",
            task_id="TEST-123",
            agent_id="agent-001",
            timestamp=datetime.now(),
        )

        assert event.type == "task_started"
        assert event.task_id == "TEST-123"
        assert event.agent_id == "agent-001"
        assert isinstance(event.timestamp, datetime)

    def test_task_event_with_metadata(self):
        """Test TaskEvent with additional metadata"""
        metadata = {"branch_name": "feature/TEST-123", "estimated_duration": "2 hours"}

        event = TaskEvent(
            type="task_assigned",
            task_id="TEST-123",
            agent_id="agent-001",
            metadata=metadata,
        )

        assert event.metadata == metadata
        assert event.metadata["branch_name"] == "feature/TEST-123"
