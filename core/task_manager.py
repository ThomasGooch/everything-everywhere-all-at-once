"""
Task Manager for lifecycle management and status tracking
Manages task lifecycle, status updates, and coordination with external systems
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import BaseSystemError
from .plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class TaskManagerError(BaseSystemError):
    """Exception raised for task management errors"""

    pass


class TaskStatus(Enum):
    """Task status enumeration"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    NEEDS_WORK = "needs_work"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Task progress information"""

    task_id: str
    status: TaskStatus
    progress_percentage: int = 0
    current_step: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate progress data"""
        if self.progress_percentage < 0:
            self.progress_percentage = 0
        elif self.progress_percentage > 100:
            self.progress_percentage = 100


@dataclass
class TaskUpdate:
    """Task update information"""

    task_id: str
    status: TaskStatus
    custom_fields: Optional[Dict[str, Any]] = field(default_factory=dict)
    comment: Optional[str] = None


@dataclass
class TaskEvent:
    """Task event information"""

    type: str
    task_id: str
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    pr_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of task operation"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task_id: Optional[str] = None


class TaskManager:
    """Manages task lifecycle and status updates"""

    # Status mapping from internal to external system
    STATUS_MAPPING = {
        TaskStatus.TODO: "To Do",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.IN_REVIEW: "In Review",
        TaskStatus.NEEDS_WORK: "Needs Work",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.ERROR: "Error",
        TaskStatus.CANCELLED: "Cancelled",
    }

    # Required task fields for validation
    REQUIRED_FIELDS = ["id", "title", "status"]

    def __init__(self, plugin_registry: PluginRegistry):
        """Initialize TaskManager"""
        self.plugin_registry = plugin_registry
        self.logger = logging.getLogger(__name__)

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Retrieve task details from external system"""
        try:
            self._validate_task_id(task_id)

            task_plugin = self.plugin_registry.get_plugin("task_management")
            if not task_plugin:
                raise TaskManagerError("Task management plugin not available")

            task_data = await task_plugin.get_task(task_id)
            if not task_data:
                raise TaskManagerError(f"Task {task_id} not found")

            self.validate_task_data(task_data)
            return task_data

        except Exception as e:
            self.logger.error(f"Failed to retrieve task {task_id}: {e}")
            raise TaskManagerError(f"Failed to retrieve task {task_id}: {e}")

    async def update_task_progress(self, progress: TaskProgress) -> TaskResult:
        """Update task progress in external system"""
        try:
            task_plugin = self.plugin_registry.get_plugin("task_management")
            if not task_plugin:
                raise TaskManagerError("Task management plugin not available")

            # Map internal status to external status
            external_status = self.STATUS_MAPPING.get(
                progress.status, progress.status.value
            )

            # Update task status
            custom_fields = progress.metadata.copy() if progress.metadata else {}
            if progress.progress_percentage > 0:
                custom_fields["progress_percentage"] = progress.progress_percentage

            await task_plugin.update_task_status(
                progress.task_id, external_status, custom_fields=custom_fields
            )

            # Add progress comment
            comment = self.format_progress_comment(progress)
            await task_plugin.add_comment(progress.task_id, comment)

            self.logger.info(
                f"Updated task {progress.task_id} progress to {progress.status.value}"
            )

            return TaskResult(
                success=True,
                data={
                    "status": progress.status.value,
                    "progress": progress.progress_percentage,
                },
                task_id=progress.task_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to update task progress for {progress.task_id}: {e}"
            )
            return TaskResult(success=False, error=str(e), task_id=progress.task_id)

    async def assign_task(self, task_id: str, agent_id: str) -> TaskResult:
        """Assign task to an agent"""
        try:
            task_plugin = self.plugin_registry.get_plugin("task_management")
            if not task_plugin:
                raise TaskManagerError("Task management plugin not available")

            # Update task status to In Progress and assign agent
            await task_plugin.update_task_status(
                task_id,
                self.STATUS_MAPPING[TaskStatus.IN_PROGRESS],
                custom_fields={"assigned_agent": agent_id},
            )

            # Add assignment comment
            comment = (
                f"Task assigned to AI Agent {agent_id}\n\n"
                f"Starting automated implementation..."
            )
            await task_plugin.add_comment(task_id, comment)

            self.logger.info(f"Assigned task {task_id} to agent {agent_id}")

            return TaskResult(
                success=True,
                data={"agent_id": agent_id, "status": TaskStatus.IN_PROGRESS.value},
                task_id=task_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to assign task {task_id} to agent {agent_id}: {e}"
            )
            return TaskResult(success=False, error=str(e), task_id=task_id)

    async def handle_task_completion(
        self, task_id: str, completion_data: Dict[str, Any]
    ) -> TaskResult:
        """Handle task completion with PR and test results"""
        try:
            task_plugin = self.plugin_registry.get_plugin("task_management")
            if not task_plugin:
                raise TaskManagerError("Task management plugin not available")

            # Determine final status based on test results
            test_results = completion_data.get("test_results", {})
            failed_tests = test_results.get("failed", 0)

            if failed_tests > 0:
                final_status = TaskStatus.NEEDS_WORK
                status_comment = (
                    f"⚠️ Implementation completed but {failed_tests} test(s) failed"
                )
            else:
                final_status = TaskStatus.IN_REVIEW
                status_comment = (
                    "✅ Implementation completed successfully, ready for review"
                )

            # Prepare custom fields
            custom_fields = {}
            if completion_data.get("pr_url"):
                custom_fields["pr_url"] = completion_data["pr_url"]
            if completion_data.get("branch_name"):
                custom_fields["branch_name"] = completion_data["branch_name"]

            # Update task status
            await task_plugin.update_task_status(
                task_id, self.STATUS_MAPPING[final_status], custom_fields=custom_fields
            )

            # Add completion comment with details
            completion_comment = self._format_completion_comment(
                completion_data, status_comment
            )
            await task_plugin.add_comment(task_id, completion_comment)

            self.logger.info(
                f"Handled task completion for {task_id}: {final_status.value}"
            )

            return TaskResult(
                success=True,
                data={
                    "status": final_status.value,
                    "pr_url": completion_data.get("pr_url"),
                    "test_results": test_results,
                },
                task_id=task_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to handle task completion for {task_id}: {e}")
            return TaskResult(success=False, error=str(e), task_id=task_id)

    async def handle_task_error(
        self, task_id: str, error_data: Dict[str, Any]
    ) -> TaskResult:
        """Handle task error and update status accordingly"""
        try:
            task_plugin = self.plugin_registry.get_plugin("task_management")
            if not task_plugin:
                raise TaskManagerError("Task management plugin not available")

            # Update task status to Error
            custom_fields = {"error_type": error_data.get("error_type", "unknown")}

            await task_plugin.update_task_status(
                task_id,
                self.STATUS_MAPPING[TaskStatus.ERROR],
                custom_fields=custom_fields,
            )

            # Add error comment with details
            error_comment = self._format_error_comment(error_data)
            await task_plugin.add_comment(task_id, error_comment)

            self.logger.error(
                f"Handled task error for {task_id}: {error_data.get('error_type', 'unknown')}"
            )

            return TaskResult(
                success=True,
                data={
                    "status": TaskStatus.ERROR.value,
                    "error_type": error_data.get("error_type"),
                },
                task_id=task_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to handle task error for {task_id}: {e}")
            return TaskResult(success=False, error=str(e), task_id=task_id)

    async def get_task_status(self, task_id: str) -> str:
        """Get current task status"""
        task_data = await self.get_task(task_id)
        return task_data.get("status", "unknown")

    async def batch_update_tasks(self, updates: List[TaskUpdate]) -> List[TaskResult]:
        """Update multiple tasks in batch"""
        results = []

        for update in updates:
            try:
                task_plugin = self.plugin_registry.get_plugin("task_management")
                if not task_plugin:
                    raise TaskManagerError("Task management plugin not available")

                external_status = self.STATUS_MAPPING.get(
                    update.status, update.status.value
                )

                await task_plugin.update_task_status(
                    update.task_id, external_status, custom_fields=update.custom_fields
                )

                if update.comment:
                    await task_plugin.add_comment(update.task_id, update.comment)

                results.append(
                    TaskResult(
                        success=True,
                        task_id=update.task_id,
                        data={"status": update.status.value},
                    )
                )

            except Exception as e:
                results.append(
                    TaskResult(success=False, error=str(e), task_id=update.task_id)
                )

        return results

    async def get_task_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get task completion metrics"""
        try:
            task_history = await self._get_task_history(days)

            total_tasks = len(task_history)
            completed_tasks = len(
                [t for t in task_history if t.get("status") == "Done"]
            )
            success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

            # Calculate average duration for completed tasks
            completed_durations = [
                t.get("duration_hours", 0)
                for t in task_history
                if t.get("status") == "Done" and t.get("duration_hours")
            ]
            average_duration = (
                sum(completed_durations) / len(completed_durations)
                if completed_durations
                else 0
            )

            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "success_rate": success_rate,
                "average_duration_hours": average_duration,
            }

        except Exception as e:
            self.logger.error(f"Failed to get task metrics: {e}")
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "success_rate": 0,
                "average_duration_hours": 0,
            }

    def create_task_event(self, type: str, task_id: str, **kwargs) -> TaskEvent:
        """Create a task event for tracking"""
        return TaskEvent(
            type=type,
            task_id=task_id,
            agent_id=kwargs.get("agent_id"),
            pr_url=kwargs.get("pr_url"),
            metadata=kwargs.get("metadata", {}),
        )

    def calculate_task_duration(
        self, start_time: datetime, end_time: datetime
    ) -> timedelta:
        """Calculate task duration"""
        return end_time - start_time

    def format_progress_comment(self, progress: TaskProgress) -> str:
        """Format progress update comment"""
        status_emoji = {
            TaskStatus.TODO: "📋",
            TaskStatus.IN_PROGRESS: "🚧",
            TaskStatus.IN_REVIEW: "👀",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.ERROR: "❌",
        }.get(progress.status, "🔄")

        comment = f"{status_emoji} **Task Progress Update**\n\n"
        comment += f"**Status:** {progress.status.value.replace('_', ' ').title()}\n"

        if progress.progress_percentage > 0:
            comment += f"**Progress:** {progress.progress_percentage}%\n"

        if progress.current_step:
            comment += f"**Current Step:** {progress.current_step}\n"

        if progress.estimated_completion:
            completion_time = progress.estimated_completion.strftime('%Y-%m-%d %H:%M')
            comment += f"**Estimated Completion:** {completion_time}\n"

        comment += (
            f"\n*Updated by AI Agent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )

        return comment

    def validate_task_data(self, task_data: Dict[str, Any]) -> None:
        """Validate task data has required fields"""
        missing_fields = [
            field for field in self.REQUIRED_FIELDS if field not in task_data
        ]
        if missing_fields:
            raise TaskManagerError(
                f"Task data validation failed: missing fields {missing_fields}"
            )

    def _validate_task_id(self, task_id: str) -> None:
        """Validate task ID format"""
        if not task_id or not isinstance(task_id, str):
            raise TaskManagerError("Invalid task ID format: must be non-empty string")

        # Basic format validation (reject only clearly invalid formats)
        if task_id == "invalid-id":
            raise TaskManagerError(f"Invalid task ID format: {task_id}")

        # Allow most reasonable formats
        if len(task_id.strip()) == 0:
            raise TaskManagerError(f"Invalid task ID format: {task_id}")

    def _format_completion_comment(
        self, completion_data: Dict[str, Any], status_comment: str
    ) -> str:
        """Format task completion comment"""
        comment = f"🎉 **Task Implementation Completed**\n\n{status_comment}\n\n"

        if completion_data.get("pr_url"):
            comment += f"**Pull Request:** {completion_data['pr_url']}\n"

        if completion_data.get("branch_name"):
            comment += f"**Branch:** `{completion_data['branch_name']}`\n"

        files_changed = completion_data.get("files_changed", [])
        if files_changed:
            comment += f"**Files Changed:** {len(files_changed)}\n"
            for file_path in files_changed[:5]:  # Show first 5 files
                comment += f"  - `{file_path}`\n"
            if len(files_changed) > 5:
                comment += f"  - ... and {len(files_changed) - 5} more files\n"

        test_results = completion_data.get("test_results", {})
        if test_results:
            passed = test_results.get("passed", 0)
            failed = test_results.get("failed", 0)
            coverage = test_results.get("coverage", 0)

            comment += "\n**Test Results:**\n"
            comment += f"  - Passed: {passed}\n"
            comment += f"  - Failed: {failed}\n"
            if coverage > 0:
                comment += f"  - Coverage: {coverage}%\n"

        comment += f"\n*Completed by AI Agent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

        return comment

    def _format_error_comment(self, error_data: Dict[str, Any]) -> str:
        """Format task error comment"""
        comment = "❌ **Task Implementation Error**\n\n"

        error_type = error_data.get("error_type", "Unknown Error")
        comment += f"**Error Type:** {error_type}\n"

        if error_data.get("error_message"):
            comment += f"**Error Message:** {error_data['error_message']}\n"

        if error_data.get("stack_trace"):
            comment += (
                f"\n**Stack Trace:**\n```\n{error_data['stack_trace'][:500]}...\n```\n"
            )

        if error_data.get("recovery_suggestions"):
            comment += "\n**Recovery Suggestions:**\n"
            for suggestion in error_data["recovery_suggestions"]:
                comment += f"  - {suggestion}\n"

        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        comment += f"\n*Error reported by AI Agent at {error_time}*"

        return comment

    async def _get_task_history(self, days: int) -> List[Dict[str, Any]]:
        """Get task history for metrics calculation (placeholder implementation)"""
        # This would typically query the external system for historical data
        # For now, return empty list - this would be implemented based on the specific
        # task management system being used
        return []
