"""Integration tests for enhanced plugins working together"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_interface import PluginResult
from plugins.confluence_plugin import ConfluencePlugin
from plugins.github_plugin import GitHubPlugin
from plugins.jira_plugin import JiraPlugin


@pytest.mark.integration
class TestEnhancedPluginsIntegration:
    """Test integration between enhanced plugins"""

    @pytest.fixture
    def jira_config(self):
        """Jira configuration for integration testing"""
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
    def github_config(self):
        """GitHub configuration for integration testing"""
        return {
            "connection": {
                "token": "ghp_test_token_123",
                "api_url": "https://api.github.com",
            },
            "options": {
                "timeout": 60,
                "default_branch": "main",
                "branch_strategies": {
                    "feature": "feature/{task_id}-{title_slug}",
                    "hotfix": "hotfix/{task_id}-{title_slug}",
                },
                "auto_reviewers": {
                    "rules": [
                        {"path_pattern": "*.py", "reviewers": ["python-team"]},
                        {"path_pattern": "*.js", "reviewers": ["frontend-team"]},
                        {"size_threshold": 500, "reviewers": ["senior-dev"]},
                    ]
                },
            },
        }

    @pytest.fixture
    def confluence_config(self):
        """Confluence configuration for integration testing"""
        return {
            "connection": {
                "url": "https://test.atlassian.net/wiki",
                "email": "test@example.com",
                "api_token": "test-token",
            },
            "options": {
                "default_space": "TEST",
                "page_templates": {
                    "api_documentation": "api_doc_template.html",
                    "user_guide": "user_guide_template.html",
                },
                "auto_labels": {"ai_generated": True},
            },
        }

    @pytest.fixture
    def jira_plugin(self, jira_config):
        """Create Jira plugin instance"""
        return JiraPlugin(jira_config)

    @pytest.fixture
    def github_plugin(self, github_config):
        """Create GitHub plugin instance"""
        return GitHubPlugin(github_config)

    @pytest.fixture
    def confluence_plugin(self, confluence_config):
        """Create Confluence plugin instance"""
        return ConfluencePlugin(confluence_config)

    @pytest.mark.asyncio
    async def test_all_plugins_initialization(
        self, jira_plugin, github_plugin, confluence_plugin
    ):
        """Test that all enhanced plugins initialize correctly"""

        # Test plugin types
        assert jira_plugin.get_plugin_type() == PluginType.TASK_MANAGEMENT
        assert github_plugin.get_plugin_type() == PluginType.VERSION_CONTROL
        assert confluence_plugin.get_plugin_type() == PluginType.DOCUMENTATION

        # Test plugin names
        assert jira_plugin.get_plugin_name() == "jira"
        assert github_plugin.get_plugin_name() == "github"
        assert confluence_plugin.get_plugin_name() == "confluence"

    @pytest.mark.asyncio
    async def test_development_workflow_simulation(
        self, jira_plugin, github_plugin, confluence_plugin
    ):
        """Test simulated development workflow using all plugins"""

        # Simulate development workflow:
        # 1. Get task from Jira
        # 2. Create GitHub branch and PR
        # 3. Create documentation in Confluence

        # Setup plugin states
        for plugin in [jira_plugin, github_plugin, confluence_plugin]:
            plugin._is_initialized = True
            plugin._connection_established = True
            plugin._session = MagicMock()

        github_plugin._base_url = "https://api.github.com"
        confluence_plugin._base_url = "https://test.atlassian.net/wiki"

        # Step 1: Get task from Jira (using basic method which works)
        with patch.object(jira_plugin, "_session") as mock_jira_session:
            mock_jira_response = MagicMock()
            mock_jira_response.status = 200
            mock_jira_response.json = AsyncMock(
                return_value={
                    "id": "12345",
                    "key": "DEV-123",
                    "fields": {
                        "summary": "Implement new feature",
                        "description": "Add new API endpoint",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Developer"},
                        "customfield_10001": 8,  # story points
                        "customfield_10003": "Alpha Team",  # team
                    },
                }
            )
            mock_jira_session.get.return_value.__aenter__.return_value = (
                mock_jira_response
            )

            task_result = await jira_plugin.get_task("DEV-123")

            assert task_result.success
            assert task_result.data["task_id"] == "DEV-123"
            assert task_result.data["title"] == "Implement new feature"
            task_data = task_result.data

        # Step 2: Create GitHub branch using enhanced functionality
        branch_name = github_plugin._generate_branch_name(
            strategy="feature", task_id="DEV-123", title_slug="implement-new-feature"
        )
        assert branch_name == "feature/DEV-123-implement-new-feature"

        # Test auto-reviewer assignment
        file_changes = {
            "modified": ["src/api.py", "frontend/component.js"],
            "created": ["tests/test_api.py"],
            "deleted": [],
        }
        reviewers = github_plugin._get_auto_reviewers(file_changes)
        assert "python-team" in reviewers
        assert "frontend-team" in reviewers

        # Step 3: Create documentation in Confluence
        with patch.object(
            confluence_plugin, "_session"
        ) as mock_conf_session, patch.object(
            confluence_plugin, "add_page_labels"
        ) as mock_add_labels:
            mock_conf_response = MagicMock()
            mock_conf_response.status = 200
            mock_conf_response.json = AsyncMock(
                return_value={
                    "id": "doc123",
                    "title": "DEV-123 Implementation Documentation",
                    "version": {"number": 1},
                    "_links": {"webui": "/pages/doc123"},
                }
            )
            mock_conf_session.post.return_value.__aenter__.return_value = (
                mock_conf_response
            )
            mock_add_labels.return_value = PluginResult(
                success=True, data={"labels": ["dev-123", "api"]}
            )

            doc_data = {
                "space_key": "TEST",
                "title": f"{task_data['task_id']} Implementation Documentation",
                "content": f"<h1>{task_data['title']}</h1><p>Implementation details for {task_data['task_id']}</p>",
                "labels": [task_data["task_id"].lower(), "api"],
            }

            doc_result = await confluence_plugin.create_page_enhanced(doc_data)

            assert doc_result.success
            assert doc_result.data["page_id"] == "doc123"
            assert doc_result.data["title"] == "DEV-123 Implementation Documentation"

    @pytest.mark.asyncio
    async def test_template_rendering_integration(self, confluence_plugin):
        """Test template rendering with real data"""

        # Test API documentation template
        template_data = {
            "template_type": "api_documentation",
            "space_key": "TEST",
            "title": "User Management API v2.0",
            "variables": {
                "api_name": "User Management API",
                "version": "v2.0",
                "endpoints": [
                    "GET /users",
                    "POST /users",
                    "PUT /users/{id}",
                    "DELETE /users/{id}",
                ],
            },
        }

        with patch.object(confluence_plugin, "create_page_enhanced") as mock_create:
            mock_create.return_value = PluginResult(
                success=True,
                data={
                    "page_id": "api123",
                    "page_url": "https://test.atlassian.net/pages/api123",
                    "title": "User Management API v2.0",
                    "version": 1,
                },
            )

            result = await confluence_plugin.create_page_from_template(template_data)

            assert result.success
            assert result.data["page_id"] == "api123"

            # Verify that template was rendered with variables
            call_args = mock_create.call_args[0][0]
            assert "User Management API" in call_args["content"]
            assert "v2.0" in call_args["content"]
            assert "template-generated" in call_args["labels"]

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, github_plugin):
        """Test error handling across plugin integrations"""

        # Setup plugin state
        github_plugin._is_initialized = True
        github_plugin._connection_established = True
        github_plugin._session = MagicMock()
        github_plugin._base_url = "https://api.github.com"

        # Test error handling in GitHub plugin
        with patch.object(github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 404  # Not found
            mock_response.text = AsyncMock(return_value="Repository not found")
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await github_plugin.analyze_repository_structure(
                repository="nonexistent/repo", branch="main"
            )

            assert not result.success
            assert "Failed to analyze repository" in result.error

    @pytest.mark.asyncio
    async def test_plugin_health_checks_integration(
        self, jira_plugin, github_plugin, confluence_plugin
    ):
        """Test health checks for all enhanced plugins"""

        plugins = [
            (jira_plugin, "Jira"),
            (github_plugin, "GitHub"),
            (confluence_plugin, "Confluence"),
        ]

        for plugin, name in plugins:
            # Setup healthy state
            plugin._is_initialized = True
            plugin._connection_established = True
            plugin._session = MagicMock()

            with patch.object(plugin, "_session") as mock_session:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_session.get.return_value.__aenter__.return_value = mock_response

                status = await plugin.health_check()
                assert (
                    status == PluginStatus.HEALTHY
                ), f"{name} plugin should be healthy"

    def test_configuration_validation_integration(
        self, jira_plugin, github_plugin, confluence_plugin
    ):
        """Test configuration validation for all plugins"""

        # All plugins should validate their configurations successfully
        assert jira_plugin.validate_config() is True
        assert github_plugin.validate_config() is True
        assert confluence_plugin.validate_config() is True

    @pytest.mark.asyncio
    async def test_concurrent_plugin_operations(self, github_plugin, confluence_plugin):
        """Test concurrent operations across plugins"""

        # Setup plugin states
        for plugin in [github_plugin, confluence_plugin]:
            plugin._is_initialized = True
            plugin._connection_established = True
            plugin._session = MagicMock()

        github_plugin._base_url = "https://api.github.com"
        confluence_plugin._base_url = "https://test.atlassian.net/wiki"

        # Mock successful responses for both plugins
        with patch.object(
            github_plugin, "_session"
        ) as mock_github_session, patch.object(
            confluence_plugin, "_session"
        ) as mock_conf_session:
            # GitHub repository analysis mock
            mock_github_response = MagicMock()
            mock_github_response.status = 200
            mock_github_response.json = AsyncMock(
                return_value={
                    "tree": [
                        {"path": "src/main.py", "type": "blob"},
                        {"path": "package.json", "type": "blob"},
                    ]
                }
            )
            mock_github_session.get.return_value.__aenter__.return_value = (
                mock_github_response
            )

            # Confluence page search mock
            mock_conf_response = MagicMock()
            mock_conf_response.status = 200
            mock_conf_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "123",
                            "title": "API Docs",
                            "_links": {"webui": "/pages/123"},
                        }
                    ],
                    "size": 1,
                }
            )
            mock_conf_session.get.return_value.__aenter__.return_value = (
                mock_conf_response
            )

            # Run concurrent operations
            import asyncio

            github_task = github_plugin.analyze_repository_structure(
                "test/repo", "main"
            )
            confluence_task = confluence_plugin.search_pages("API", space_key="TEST")

            github_result, confluence_result = await asyncio.gather(
                github_task, confluence_task
            )

            # Verify both operations succeeded
            assert github_result.success
            assert "Python" in github_result.data["analysis"]["languages"]
            assert "JavaScript" in github_result.data["analysis"]["languages"]

            assert confluence_result.success
            assert len(confluence_result.data["pages"]) == 1
            assert confluence_result.data["pages"][0]["title"] == "API Docs"
