"""Tests for Jira tools module."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from plugins.jira.tools import (
    jira_add_comment,
    jira_assign_task,
    jira_create_task,
    jira_get_my_tasks,
    jira_get_task,
    jira_search_tasks,
    jira_transition_task,
    jira_update_status,
    register_tools,
)


class TestJiraToolsRegistration:
    """Test suite for Jira tools registration."""

    @patch.dict("os.environ", {}, clear=True)
    def test_register_tools_no_config(self):
        """Test tool registration without Jira configuration."""
        tools = register_tools()
        assert tools == {}

    @patch.dict("os.environ", {"JIRA_API_KEY": "test_key"}, clear=True)
    def test_register_tools_with_api_key(self):
        """Test tool registration with JIRA_API_KEY."""
        tools = register_tools()

        expected_tools = {
            "jira_get_task",
            "jira_search_tasks",
            "jira_get_my_tasks",
            "jira_update_status",
            "jira_create_task",
            "jira_assign_task",
            "jira_add_comment",
            "jira_transition_task",
        }

        assert set(tools.keys()) == expected_tools
        assert all(callable(tool) for tool in tools.values())

    @patch.dict("os.environ", {"JIRA_API_TOKEN": "test_token"}, clear=True)
    def test_register_tools_with_api_token(self):
        """Test tool registration with JIRA_API_TOKEN."""
        tools = register_tools()
        assert len(tools) == 8
        assert "jira_get_task" in tools


class TestJiraTools:
    """Test suite for individual Jira tool functions."""

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_get_task_success(self, mock_jira_api):
        """Test successful task retrieval."""
        mock_api_instance = Mock()
        mock_api_instance.get_issue.return_value = {
            "key": "TEST-123",
            "fields": {"summary": "Test task"},
            "success": True,
        }
        mock_jira_api.return_value = mock_api_instance

        result = jira_get_task("TEST-123")

        mock_api_instance.get_issue.assert_called_once_with("TEST-123")
        assert result["key"] == "TEST-123"
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_get_task_error(self, mock_jira_api):
        """Test task retrieval error handling."""
        mock_jira_api.side_effect = Exception("API Error")

        result = jira_get_task("TEST-123")

        assert result["error"] == "API Error"
        assert result["success"] is False

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_update_status_success(self, mock_jira_api):
        """Test successful status update."""
        mock_api_instance = Mock()
        mock_api_instance.transition_issue.return_value = {"success": True}
        mock_jira_api.return_value = mock_api_instance

        result = jira_update_status("TEST-123", "In Progress")

        mock_api_instance.transition_issue.assert_called_once_with(
            "TEST-123", "In Progress"
        )
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_update_status_error(self, mock_jira_api):
        """Test status update error handling."""
        mock_jira_api.side_effect = Exception("Transition Error")

        result = jira_update_status("TEST-123", "Done")

        assert result["error"] == "Transition Error"
        assert result["success"] is False

    @patch("plugins.jira.tools.JiraAPI")
    @patch("asyncio.run")
    def test_jira_search_tasks_success(self, mock_asyncio_run, mock_jira_api):
        """Test successful task search."""
        mock_api_instance = Mock()
        mock_asyncio_run.return_value = {
            "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
            "total": 2,
            "success": True,
        }
        mock_jira_api.return_value = mock_api_instance

        result = jira_search_tasks("project = TEST")

        mock_asyncio_run.assert_called_once()
        assert result["total"] == 2
        assert len(result["issues"]) == 2
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_search_tasks_error(self, mock_jira_api):
        """Test search tasks error handling."""
        mock_jira_api.side_effect = Exception("Search Error")

        result = jira_search_tasks("invalid jql")

        assert result["error"] == "Search Error"
        assert result["success"] is False
        assert result["issues"] == []
        assert result["total"] == 0

    @patch("plugins.jira.tools.JiraAPI")
    @patch("asyncio.run")
    def test_jira_get_my_tasks_success(self, mock_asyncio_run, mock_jira_api):
        """Test successful my tasks retrieval."""
        mock_api_instance = Mock()
        mock_asyncio_run.return_value = {
            "issues": [{"key": "TEST-1", "fields": {"assignee": {"name": "user"}}}],
            "total": 1,
            "success": True,
        }
        mock_jira_api.return_value = mock_api_instance

        result = jira_get_my_tasks()

        mock_asyncio_run.assert_called_once()
        assert result["total"] == 1
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_get_my_tasks_error(self, mock_jira_api):
        """Test my tasks error handling."""
        mock_jira_api.side_effect = Exception("My tasks Error")

        result = jira_get_my_tasks()

        assert result["error"] == "My tasks Error"
        assert result["success"] is False
        assert result["issues"] == []
        assert result["total"] == 0

    def test_jira_create_task(self):
        """Test task creation (mock implementation)."""
        result = jira_create_task("TEST", "New task", "Description")

        assert result["key"] == "TEST-123"
        assert result["summary"] == "New task"
        assert result["description"] == "Description"
        assert result["success"] is True

    def test_jira_assign_task(self):
        """Test task assignment (mock implementation)."""
        result = jira_assign_task("TEST-123", "john.doe")

        assert result["task_id"] == "TEST-123"
        assert result["assignee"] == "john.doe"
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_add_comment_success(self, mock_jira_api):
        """Test successful comment addition."""
        mock_api_instance = Mock()
        mock_api_instance.add_comment.return_value = {"success": True}
        mock_jira_api.return_value = mock_api_instance

        result = jira_add_comment("TEST-123", "Test comment")

        mock_api_instance.add_comment.assert_called_once_with(
            "TEST-123", "Test comment"
        )
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_add_comment_error(self, mock_jira_api):
        """Test comment addition error handling."""
        mock_jira_api.side_effect = Exception("Comment Error")

        result = jira_add_comment("TEST-123", "Test comment")

        assert result["error"] == "Comment Error"
        assert result["success"] is False

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_transition_task_success(self, mock_jira_api):
        """Test successful task transition."""
        mock_api_instance = Mock()
        mock_api_instance.transition_issue.return_value = {"success": True}
        mock_jira_api.return_value = mock_api_instance

        result = jira_transition_task("TEST-123", "Done")

        mock_api_instance.transition_issue.assert_called_once_with("TEST-123", "Done")
        assert result["success"] is True

    @patch("plugins.jira.tools.JiraAPI")
    def test_jira_transition_task_error(self, mock_jira_api):
        """Test task transition error handling."""
        mock_jira_api.side_effect = Exception("Transition Error")

        result = jira_transition_task("TEST-123", "Done")

        assert result["error"] == "Transition Error"
        assert result["success"] is False
