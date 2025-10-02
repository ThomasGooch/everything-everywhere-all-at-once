"""Enhanced unit tests for Jira Plugin advanced features"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_interface import PluginResult
from plugins.jira_plugin import JiraPlugin


@pytest.mark.integration
class TestJiraPluginEnhanced:
    """Test advanced Jira plugin features"""

    @pytest.fixture
    def enhanced_jira_config(self):
        """Enhanced Jira configuration for testing"""
        return {
            "connection": {
                "url": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test-token",
            },
            "options": {
                "timeout": 30,
                "retry_attempts": 3,
                "include_subtasks": True,
                "include_linked_issues": True,
                "custom_fields": {
                    "story_points": "customfield_10001",
                    "epic_link": "customfield_10002",
                    "team": "customfield_10003",
                },
            },
        }

    @pytest.fixture
    def enhanced_jira_plugin(self, enhanced_jira_config):
        """Create enhanced Jira plugin instance"""
        return JiraPlugin(enhanced_jira_config)

    @pytest.fixture
    def mock_task_with_subtasks(self):
        """Mock Jira task response with subtasks"""
        return {
            "id": "12345",
            "key": "TEST-123",
            "fields": {
                "summary": "Main Task",
                "description": "Main task description",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "Test User"},
                "customfield_10001": 8,  # story points
                "customfield_10002": "TEST-100",  # epic link
                "customfield_10003": "Alpha Team",  # team
                "subtasks": [
                    {
                        "id": "12346",
                        "key": "TEST-124",
                        "fields": {"summary": "Subtask 1", "status": {"name": "Done"}},
                    }
                ],
                "issuelinks": [
                    {
                        "type": {"name": "Blocks", "inward": "is blocked by"},
                        "inwardIssue": {
                            "key": "TEST-125",
                            "fields": {"summary": "Blocking Issue"},
                        },
                    }
                ],
            },
        }

    # RED: Test for get_task_with_context - should fail initially
    @pytest.mark.asyncio
    async def test_get_task_with_context_includes_subtasks_and_links(
        self, enhanced_jira_plugin, mock_task_with_subtasks
    ):
        """Test getting task with full context including subtasks and linked issues"""

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_task_with_subtasks)
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.get_task_with_context(
                task_id="TEST-123",
                include_subtasks=True,
                include_linked_issues=True,
                include_comments=True,
            )

            assert result.success
            task_data = result.data

            # Verify main task data
            assert task_data["key"] == "TEST-123"
            assert task_data["summary"] == "Main Task"

            # Verify custom fields are mapped
            assert task_data["story_points"] == 8
            assert task_data["epic_link"] == "TEST-100"
            assert task_data["team"] == "Alpha Team"

            # Verify subtasks are included
            assert "subtasks" in task_data
            assert len(task_data["subtasks"]) == 1
            assert task_data["subtasks"][0]["key"] == "TEST-124"

            # Verify linked issues are included
            assert "linked_issues" in task_data
            assert len(task_data["linked_issues"]) == 1
            assert task_data["linked_issues"][0]["key"] == "TEST-125"

    # RED: Test for advanced progress tracking
    @pytest.mark.asyncio
    async def test_add_progress_comment_with_template(self, enhanced_jira_plugin):
        """Test adding progress comment using template"""

        progress_data = {
            "steps_completed": ["analyze_codebase", "generate_plan"],
            "current_step": "generate_code",
            "estimated_completion": "2024-12-01T10:00:00Z",
            "ai_cost": 0.45,
            "files_changed": ["src/main.py", "tests/test_main.py"],
        }

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(
                return_value={
                    "id": "comment-123",
                    "author": {"displayName": "Test User"},
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.add_progress_comment(
                task_id="TEST-123",
                progress_data=progress_data,
                template="ai_agent_progress",
            )

            assert result.success
            assert "comment_id" in result.data

            # Verify the comment content was properly templated
            call_args = mock_session.post.call_args
            comment_body = call_args[1]["json"]["body"]

            assert "🤖 **AI Agent Progress Update**" in comment_body
            assert "analyze_codebase ✅" in comment_body
            assert "generate_plan ✅" in comment_body
            assert "generate_code 🚧" in comment_body
            assert "$0.45" in comment_body
            assert "src/main.py" in comment_body

    # RED: Test for custom field management
    @pytest.mark.asyncio
    async def test_update_custom_fields(self, enhanced_jira_plugin):
        """Test updating custom fields with mapped field names"""

        custom_fields = {"story_points": 5, "team": "Beta Team", "ai_generated": True}

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"id": "TEST-123"})
            mock_session.put.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.update_custom_fields(
                task_id="TEST-123", custom_fields=custom_fields
            )

            assert result.success

            # Verify custom fields were mapped correctly in the API call
            call_args = mock_session.put.call_args
            fields_data = json.loads(call_args[1]["data"])["fields"]

            assert fields_data["customfield_10001"] == 5  # story_points
            assert fields_data["customfield_10003"] == "Beta Team"  # team
            # ai_generated should be mapped to a new custom field

    # RED: Test for transition validation
    @pytest.mark.asyncio
    async def test_get_available_transitions(self, enhanced_jira_plugin):
        """Test getting available status transitions for a task"""

        mock_transitions = {
            "transitions": [
                {
                    "id": "21",
                    "name": "In Progress",
                    "to": {"name": "In Progress", "id": "3"},
                },
                {"id": "31", "name": "Done", "to": {"name": "Done", "id": "10001"}},
            ]
        }

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_transitions)
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.get_available_transitions("TEST-123")

            assert result.success
            transitions = result.data["transitions"]

            assert len(transitions) == 2
            assert transitions[0]["name"] == "In Progress"
            assert transitions[1]["name"] == "Done"

    # RED: Test for transition with validation
    @pytest.mark.asyncio
    async def test_transition_task_with_validation(self, enhanced_jira_plugin):
        """Test transitioning task with validation of allowed transitions"""

        mock_transitions = {
            "transitions": [{"id": "31", "name": "Done", "to": {"name": "Done"}}]
        }

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            # First call returns available transitions, second performs transition
            mock_get_response = MagicMock()
            mock_get_response.status = 200
            mock_get_response.json = AsyncMock(return_value=mock_transitions)

            mock_post_response = MagicMock()
            mock_post_response.status = 204
            mock_post_response.json = AsyncMock(return_value={"id": "TEST-123"})

            mock_session.get.return_value.__aenter__.return_value = mock_get_response
            mock_session.post.return_value.__aenter__.return_value = mock_post_response

            result = await enhanced_jira_plugin.transition_task_with_validation(
                task_id="TEST-123", status="Done", validate_transition=True
            )

            assert result.success
            assert mock_session.get.call_count == 1  # Check transitions
            assert mock_session.post.call_count == 1  # Perform transition

    # RED: Test for task relationship management
    @pytest.mark.asyncio
    async def test_create_subtask(self, enhanced_jira_plugin):
        """Test creating a subtask linked to parent task"""

        subtask_data = {
            "summary": "Subtask: Implementation",
            "description": "Implement the feature",
            "parent_key": "TEST-123",
        }

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(
                return_value={"key": "TEST-124", "id": "12346"}
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.create_subtask(
                project_key="TEST", subtask_data=subtask_data
            )

            assert result.success
            assert result.data["key"] == "TEST-124"

            # Verify parent link was set correctly
            call_args = mock_session.post.call_args
            fields_data = json.loads(call_args[1]["data"])["fields"]
            assert fields_data["parent"]["key"] == "TEST-123"

    # RED: Test for epic management
    @pytest.mark.asyncio
    async def test_link_to_epic(self, enhanced_jira_plugin):
        """Test linking a task to an epic"""

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"id": "TEST-123"})
            mock_session.put.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.link_to_epic(
                task_id="TEST-123", epic_key="TEST-100"
            )

            assert result.success

            # Verify epic link custom field was set
            call_args = mock_session.put.call_args
            fields_data = json.loads(call_args[1]["data"])["fields"]
            assert fields_data["customfield_10002"] == "TEST-100"  # epic_link field

    # RED: Test for rich comment templates
    @pytest.mark.asyncio
    async def test_comment_templates(self, enhanced_jira_plugin):
        """Test different comment template types"""

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(
                return_value={
                    "id": "comment-123",
                    "author": {"displayName": "Test User"},
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            # Test AI agent start template
            result = await enhanced_jira_plugin.add_templated_comment(
                task_id="TEST-123",
                template_type="ai_agent_start",
                template_data={
                    "agent_name": "Development Agent",
                    "workflow_name": "Standard Development",
                    "estimated_duration": "30-45 minutes",
                },
            )

            assert result.success

            call_args = mock_session.post.call_args
            comment_body = call_args[1]["json"]["body"]

            assert "🤖 **AI Agent Started**" in comment_body
            assert "Development Agent" in comment_body
            assert "30-45 minutes" in comment_body

    # RED: Test for batch operations
    @pytest.mark.asyncio
    async def test_batch_status_update(self, enhanced_jira_plugin):
        """Test updating status for multiple tasks in batch"""

        task_updates = [
            {"task_id": "TEST-123", "status": "In Progress"},
            {"task_id": "TEST-124", "status": "Done"},
            {"task_id": "TEST-125", "status": "In Review"},
        ]

        with patch.object(enhanced_jira_plugin, "update_task_status") as mock_update:
            mock_update.return_value = PluginResult(
                success=True, data={"updated": True}
            )

            result = await enhanced_jira_plugin.batch_update_status(task_updates)

            assert result.success
            assert result.data["updated_count"] == 3
            assert result.data["failed_count"] == 0
            assert mock_update.call_count == 3

    # RED: Test for task search and filtering
    @pytest.mark.asyncio
    async def test_search_tasks_advanced(self, enhanced_jira_plugin):
        """Test advanced task search with JQL"""

        search_criteria = {
            "project": "TEST",
            "assignee": "currentUser()",
            "status": ["In Progress", "To Do"],
            "labels": ["ai-generated"],
            "custom_fields": {"team": "Alpha Team"},
        }

        mock_search_result = {
            "issues": [
                {"key": "TEST-123", "fields": {"summary": "Task 1"}},
                {"key": "TEST-124", "fields": {"summary": "Task 2"}},
            ],
            "total": 2,
        }

        with patch.object(enhanced_jira_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_search_result)
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await enhanced_jira_plugin.search_tasks(search_criteria)

            assert result.success
            assert len(result.data["tasks"]) == 2
            assert result.data["total_count"] == 2

            # Verify JQL was constructed correctly
            call_args = mock_session.get.call_args
            assert "project = TEST" in call_args[0][0]  # URL contains JQL
            assert "assignee = currentUser()" in call_args[0][0]
