"""Basic tests for enhanced Jira plugin methods"""

import pytest

from plugins.jira_plugin import JiraPlugin


class TestJiraEnhancedBasic:
    """Basic tests for enhanced Jira functionality"""

    @pytest.fixture
    def jira_config(self):
        """Jira configuration for testing"""
        return {
            "connection": {
                "url": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test-token",
            },
            "options": {
                "custom_fields": {
                    "story_points": "customfield_10001",
                    "epic_link": "customfield_10002",
                    "team": "customfield_10003",
                }
            },
        }

    @pytest.fixture
    def jira_plugin(self, jira_config):
        """Create Jira plugin instance"""
        return JiraPlugin(jira_config)

    @pytest.mark.asyncio
    async def test_get_task_with_context_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "get_task_with_context")
        assert callable(getattr(jira_plugin, "get_task_with_context"))

    @pytest.mark.asyncio
    async def test_add_progress_comment_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "add_progress_comment")
        assert callable(getattr(jira_plugin, "add_progress_comment"))

    @pytest.mark.asyncio
    async def test_update_custom_fields_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "update_custom_fields")
        assert callable(getattr(jira_plugin, "update_custom_fields"))

    @pytest.mark.asyncio
    async def test_get_available_transitions_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "get_available_transitions")
        assert callable(getattr(jira_plugin, "get_available_transitions"))

    @pytest.mark.asyncio
    async def test_transition_task_with_validation_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "transition_task_with_validation")
        assert callable(getattr(jira_plugin, "transition_task_with_validation"))

    @pytest.mark.asyncio
    async def test_create_subtask_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "create_subtask")
        assert callable(getattr(jira_plugin, "create_subtask"))

    @pytest.mark.asyncio
    async def test_link_to_epic_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "link_to_epic")
        assert callable(getattr(jira_plugin, "link_to_epic"))

    @pytest.mark.asyncio
    async def test_batch_update_status_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "batch_update_status")
        assert callable(getattr(jira_plugin, "batch_update_status"))

    @pytest.mark.asyncio
    async def test_search_tasks_method_exists(self, jira_plugin):
        """Test that the enhanced method exists"""
        assert hasattr(jira_plugin, "search_tasks")
        assert callable(getattr(jira_plugin, "search_tasks"))

    def test_transform_task_data_basic(self, jira_plugin):
        """Test basic task data transformation"""
        mock_issue_data = {
            "id": "12345",
            "key": "TEST-123",
            "fields": {
                "summary": "Test Task",
                "description": "Test Description",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "Test User"},
                "customfield_10001": 8,  # story_points
                "customfield_10002": "TEST-100",  # epic_link
                "customfield_10003": "Alpha Team",  # team
            },
        }

        transformed = jira_plugin._transform_task_data(mock_issue_data)

        assert transformed["id"] == "12345"
        assert transformed["key"] == "TEST-123"
        assert transformed["summary"] == "Test Task"
        assert transformed["status"] == "In Progress"
        assert transformed["assignee"] == "Test User"

        # Check custom field mapping
        assert transformed["story_points"] == 8
        assert transformed["epic_link"] == "TEST-100"
        assert transformed["team"] == "Alpha Team"

    def test_render_ai_progress_template(self, jira_plugin):
        """Test AI progress template rendering"""
        progress_data = {
            "current_step": "generate_code",
            "steps_completed": ["analyze_codebase", "generate_plan"],
            "estimated_completion": "2024-12-01T10:00:00Z",
            "ai_cost": 0.45,
            "files_changed": ["src/main.py", "tests/test_main.py"],
        }

        result = jira_plugin._render_ai_progress_template(progress_data)

        assert "🤖 **AI Agent Progress Update**" in result
        assert "generate_code 🚧" in result
        assert "analyze_codebase ✅" in result
        assert "generate_plan ✅" in result
        assert "$0.45" in result
        assert "src/main.py" in result

    def test_render_ai_start_template(self, jira_plugin):
        """Test AI start template rendering"""
        template_data = {
            "agent_name": "Development Agent",
            "workflow_name": "Standard Development",
            "estimated_duration": "30-45 minutes",
            "timestamp": "2024-12-01T09:00:00Z",
        }

        result = jira_plugin._render_ai_start_template(template_data)

        assert "🤖 **AI Agent Started**" in result
        assert "Development Agent" in result
        assert "Standard Development" in result
        assert "30-45 minutes" in result

    def test_render_ai_completion_template(self, jira_plugin):
        """Test AI completion template rendering"""
        template_data = {
            "pr_number": "42",
            "pr_url": "https://github.com/user/repo/pull/42",
            "branch_name": "feature/test-123",
            "commit_hash": "abc123def456",
            "commit_url": "https://github.com/user/repo/commit/abc123def456",
            "files_modified": 3,
            "files_created": 2,
            "test_status": "✅ 15/15 passed",
        }

        result = jira_plugin._render_ai_completion_template(template_data)

        assert "🚀 **AI Implementation Completed!**" in result
        assert "[42]" in result
        assert "feature/test-123" in result
        assert "abc123d" in result  # First 7 chars of hash
        assert "Files Modified: 3" in result
        assert "Files Created: 2" in result
