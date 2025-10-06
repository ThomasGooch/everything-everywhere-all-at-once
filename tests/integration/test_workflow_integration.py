"""Integration tests for workflow system."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from workflows.real_development_workflow import WorkflowExecutor


class TestWorkflowIntegration:
    """Integration tests for the workflow system."""

    @pytest.mark.integration
    def test_workflow_executor_initialization(self):
        """Test that WorkflowExecutor initializes correctly."""
        executor = WorkflowExecutor("TEST-123")
        
        assert executor.task_id == "TEST-123"
        assert executor.temp_dir.name == "temp"
        assert executor.task_details is None
        assert executor.branch_name is None
        assert executor.jira_api is None
        assert executor.github_tools is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('workflows.real_development_workflow.JiraAPI')
    async def test_step1_initialization_integration(self, mock_jira_api):
        """Test that step 1 initializes Jira API correctly."""
        mock_api = AsyncMock()
        mock_api.get_issue_async = AsyncMock(return_value={
            'key': 'TEST-123',
            'fields': {
                'summary': 'Test task',
                'status': {'name': 'To Do'},
                'assignee': {'displayName': 'Test User'}
            }
        })
        mock_jira_api.return_value = mock_api
        
        executor = WorkflowExecutor("TEST-123")
        result = await executor.step1_fetch_task_details()
        
        assert result is True
        assert executor.jira_api is not None
        assert executor.task_details is not None
        assert executor.task_details['key'] == 'TEST-123'

    @pytest.mark.integration
    @patch('workflows.real_development_workflow.GitHubTools')
    def test_step4_github_integration(self, mock_github_tools):
        """Test that step 4 initializes GitHub tools correctly."""
        mock_tools = MagicMock()
        mock_tools.get_repository_info.return_value = {
            'repo_full_name': 'test/repo',
            'repo_url': 'https://github.com/test/repo.git'
        }
        mock_tools.setup_repository_workspace.return_value = {
            'success': True,
            'branch_name': 'TEST-123_implementation_123456',
            'workspace_dir': Path('/tmp/test'),
            'repo_url': 'https://github.com/test/repo.git'
        }
        mock_github_tools.return_value = mock_tools
        
        executor = WorkflowExecutor("TEST-123")
        executor.task_details = {'fields': {'summary': 'Test implementation'}}
        
        result = executor.step4_setup_temp_workspace()
        
        assert result is True
        assert executor.github_tools is not None
        assert executor.branch_name == 'TEST-123_implementation_123456'

    @pytest.mark.integration
    def test_workflow_directory_structure(self):
        """Test that workflow directory structure is correct."""
        # Test that we can import main workflow modules
        from workflows.real_development_workflow import WorkflowExecutor
        from workflows.complete_workflow import WorkflowExecutor as CompleteWorkflowExecutor
        from main import WorkflowRunner
        
        # Test basic instantiation
        workflow_exec = WorkflowExecutor("TEST-123")
        complete_exec = CompleteWorkflowExecutor("TEST-123")
        runner = WorkflowRunner()
        
        assert workflow_exec.task_id == "TEST-123"
        assert complete_exec.task_id == "TEST-123"
        assert runner.workflows_dir.name == "workflows"