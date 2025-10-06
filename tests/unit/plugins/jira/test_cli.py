"""Tests for Jira CLI module."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
from plugins.jira.cli import jira, get_task, update_status, create_task


class TestJiraCLI:
    """Test suite for Jira CLI commands."""
    
    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
    
    @patch('plugins.jira.cli.JiraAPI')
    def test_get_task_success(self, mock_jira_api):
        """Test successful task retrieval via CLI."""
        mock_api_instance = Mock()
        mock_api_instance.get_issue.return_value = {
            "fields": {
                "summary": "Test task",
                "status": {"name": "To Do"}
            }
        }
        mock_jira_api.return_value = mock_api_instance
        
        result = self.runner.invoke(get_task, ["TEST-123"])
        
        assert result.exit_code == 0
        assert "Task: Test task" in result.output
        assert "Status: To Do" in result.output
        mock_api_instance.get_issue.assert_called_once_with("TEST-123")
    
    @patch('plugins.jira.cli.JiraAPI')
    def test_get_task_error(self, mock_jira_api):
        """Test task retrieval error handling via CLI."""
        mock_jira_api.side_effect = Exception("API Error")
        
        result = self.runner.invoke(get_task, ["TEST-123"])
        
        assert result.exit_code == 0  # Click doesn't exit with error code by default
        assert "Error: API Error" in result.output
    
    @patch('plugins.jira.cli.JiraAPI')
    def test_update_status_success(self, mock_jira_api):
        """Test successful status update via CLI."""
        mock_api_instance = Mock()
        mock_api_instance.transition_issue.return_value = {"success": True}
        mock_jira_api.return_value = mock_api_instance
        
        result = self.runner.invoke(update_status, ["TEST-123", "In Progress"])
        
        assert result.exit_code == 0
        assert "Updated TEST-123 to In Progress" in result.output
        mock_api_instance.transition_issue.assert_called_once_with("TEST-123", "In Progress")
    
    @patch('plugins.jira.cli.JiraAPI')
    def test_update_status_failure(self, mock_jira_api):
        """Test status update failure via CLI."""
        mock_api_instance = Mock()
        mock_api_instance.transition_issue.return_value = {"success": False}
        mock_jira_api.return_value = mock_api_instance
        
        result = self.runner.invoke(update_status, ["TEST-123", "Done"])
        
        assert result.exit_code == 0
        assert "Failed to update task" in result.output
    
    @patch('plugins.jira.cli.JiraAPI')
    def test_update_status_error(self, mock_jira_api):
        """Test status update error handling via CLI."""
        mock_jira_api.side_effect = Exception("Transition Error")
        
        result = self.runner.invoke(update_status, ["TEST-123", "Done"])
        
        assert result.exit_code == 0
        assert "Error: Transition Error" in result.output
    
    def test_create_task_basic(self):
        """Test basic task creation via CLI."""
        result = self.runner.invoke(create_task, ["TEST", "New task"])
        
        assert result.exit_code == 0
        assert "Created task in TEST: New task" in result.output
    
    def test_create_task_with_description(self):
        """Test task creation with description via CLI."""
        result = self.runner.invoke(
            create_task, 
            ["TEST", "New task", "--description", "Task description"]
        )
        
        assert result.exit_code == 0
        assert "Created task in TEST: New task" in result.output
    
    def test_jira_group_command(self):
        """Test main jira group command."""
        result = self.runner.invoke(jira, ["--help"])
        
        assert result.exit_code == 0
        assert "Jira task management operations." in result.output
        assert "get-task" in result.output
        assert "update-status" in result.output
        assert "create-task" in result.output
    
    def test_get_task_help(self):
        """Test get-task command help."""
        result = self.runner.invoke(get_task, ["--help"])
        
        assert result.exit_code == 0
        assert "Get task details." in result.output
    
    def test_update_status_help(self):
        """Test update-status command help."""
        result = self.runner.invoke(update_status, ["--help"])
        
        assert result.exit_code == 0
        assert "Update task status." in result.output
    
    def test_create_task_help(self):
        """Test create-task command help."""
        result = self.runner.invoke(create_task, ["--help"])
        
        assert result.exit_code == 0
        assert "Create a new task." in result.output