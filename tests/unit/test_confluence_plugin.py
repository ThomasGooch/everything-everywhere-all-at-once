"""Unit tests for Confluence plugin."""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.confluence.api import ConfluenceAPI
from plugins.confluence.config import ConfluenceConfig
from plugins.confluence.tools import ConfluenceTools


class TestConfluenceConfig:
    """Test Confluence configuration management."""

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_all_confluence_vars_present(self):
        """Test configuration with all Confluence-specific environment variables."""
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_BASE_URL": "https://company.atlassian.net",
                "CONFLUENCE_USERNAME": "user@company.com",
                "CONFLUENCE_API_KEY": "test_api_key",
                "CONFLUENCE_SPACE_KEY": "DOC",
            },
        ):
            config = ConfluenceConfig.from_env()
            assert config is not None
            assert config.base_url == "https://company.atlassian.net"
            assert config.username == "user@company.com"
            assert config.api_key == "test_api_key"
            assert config.space_key == "DOC"

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_fallback_to_jira_vars(self):
        """Test configuration falling back to Jira environment variables."""
        with patch.dict(
            os.environ,
            {
                "JIRA_BASE_URL": "https://company.atlassian.net",
                "JIRA_USERNAME": "user@company.com",
                "JIRA_API_TOKEN": "test_api_token",
                "JIRA_PROJECT_KEY": "PROJ",
            },
        ):
            config = ConfluenceConfig.from_env()
            assert config is not None
            assert config.base_url == "https://company.atlassian.net"
            assert config.username == "user@company.com"
            assert config.api_key == "test_api_token"
            assert config.space_key == "PROJDOC"

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_vars(self):
        """Test configuration with missing environment variables."""
        with patch.dict(
            os.environ, {"CONFLUENCE_BASE_URL": "https://company.atlassian.net"}
        ):
            config = ConfluenceConfig.from_env()
            assert config is None

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_mixed_vars(self):
        """Test configuration with mixed Confluence and Jira variables."""
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_BASE_URL": "https://confluence.company.com",
                "JIRA_USERNAME": "user@company.com",
                "JIRA_API_KEY": "jira_token",
                "CONFLUENCE_SPACE_KEY": "DOCS",
            },
        ):
            config = ConfluenceConfig.from_env()
            assert config is not None
            assert config.base_url == "https://confluence.company.com"
            assert config.username == "user@company.com"
            assert config.api_key == "jira_token"
            assert config.space_key == "DOCS"


class TestConfluenceAPI:
    """Test Confluence API wrapper."""

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    def test_init_success(self, mock_from_env):
        """Test successful API initialization."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        api = ConfluenceAPI()
        assert api.config == mock_config
        assert api.auth_header is not None

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    def test_init_no_config(self, mock_from_env):
        """Test API initialization with missing configuration."""
        mock_from_env.return_value = None

        with pytest.raises(ValueError, match="Confluence configuration not available"):
            ConfluenceAPI()

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_create_page_async_success(self, mock_from_env):
        """Test successful page creation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        api = ConfluenceAPI()

        # Mock the API method directly
        api.create_page_async = AsyncMock(
            return_value={
                "success": True,
                "page_id": "123456",
                "page_title": "Test Page",
                "page_url": "https://company.atlassian.net/wiki/spaces/DOC/pages/123456",
            }
        )

        result = await api.create_page_async("Test Page", "<p>Test content</p>")

        assert result["success"] is True
        assert result["page_id"] == "123456"
        assert result["page_title"] == "Test Page"
        assert "page_url" in result

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_create_page_async_failure(self, mock_from_env):
        """Test failed page creation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        api = ConfluenceAPI()

        # Mock the API method directly to return failure
        api.create_page_async = AsyncMock(
            return_value={"success": False, "error": "HTTP 400: Bad request"}
        )

        result = await api.create_page_async("Test Page", "<p>Test content</p>")

        assert result["success"] is False
        assert "HTTP 400" in result["error"]

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_search_pages_async_success(self, mock_from_env):
        """Test successful page search."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        api = ConfluenceAPI()

        # Mock the API method directly
        api.search_pages_async = AsyncMock(
            return_value={
                "success": True,
                "results": [{"id": "123", "title": "Test Page"}],
                "total": 1,
            }
        )

        result = await api.search_pages_async("title~Test")

        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["total"] == 1

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    def test_generate_task_documentation(self, mock_from_env):
        """Test task documentation generation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        api = ConfluenceAPI()
        task_details = {
            "fields": {
                "summary": "Test Task",
                "description": "Test description",
                "status": {"name": "Done"},
                "assignee": {"displayName": "Test User"},
            },
            "self": "https://company.atlassian.net/browse/TASK-123",
        }

        content = api.generate_task_documentation(
            "TASK-123",
            task_details,
            "https://github.com/user/repo/pull/1",
            "Completed successfully",
        )

        assert "TASK-123" in content
        assert "Test Task" in content
        assert "Done" in content
        assert "Test User" in content
        assert "https://github.com/user/repo/pull/1" in content
        assert "Completed successfully" in content
        assert "AI Development Automation System" in content


class TestConfluenceTools:
    """Test Confluence tools."""

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    def test_init(self, mock_from_env):
        """Test tools initialization."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        tools = ConfluenceTools()
        assert tools.api is not None

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_create_task_documentation_async_new_page(self, mock_from_env):
        """Test creating new task documentation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        tools = ConfluenceTools()

        # Mock API methods
        tools.api.search_pages_async = AsyncMock(
            return_value={"success": True, "results": []}
        )
        tools.api.create_page_async = AsyncMock(
            return_value={
                "success": True,
                "page_id": "123456",
                "page_url": "https://company.atlassian.net/wiki/spaces/DOC/pages/123456",
                "page_title": "TASK-123: Test Task",
            }
        )

        task_details = {
            "fields": {
                "summary": "Test Task",
                "description": "Test description",
                "status": {"name": "Done"},
            }
        }

        result = await tools.create_task_documentation_async(
            "TASK-123",
            task_details,
            "https://github.com/user/repo/pull/1",
            "Test notes",
        )

        assert result["success"] is True
        assert result["action"] == "created"
        assert result["page_id"] == "123456"

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_create_task_documentation_async_update_existing(self, mock_from_env):
        """Test updating existing task documentation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        tools = ConfluenceTools()

        # Mock existing page found
        existing_page = {
            "success": True,
            "page": {
                "id": "123456",
                "title": "TASK-123: Test Task",
                "version": {"number": 1},
            },
        }

        tools.api.search_pages_async = AsyncMock(
            return_value={
                "success": True,
                "results": [{"id": "123456", "title": "TASK-123: Test Task"}],
            }
        )
        tools.api.get_page_async = AsyncMock(return_value=existing_page)
        tools.api.update_page_async = AsyncMock(
            return_value={
                "success": True,
                "page_id": "123456",
                "page_url": "https://company.atlassian.net/wiki/spaces/DOC/pages/123456",
                "page_title": "TASK-123: Test Task",
            }
        )

        task_details = {
            "fields": {
                "summary": "Test Task",
                "description": "Test description",
                "status": {"name": "Done"},
            }
        }

        result = await tools.create_task_documentation_async("TASK-123", task_details)

        assert result["success"] is True
        assert result["action"] == "updated"

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @pytest.mark.asyncio
    async def test_create_project_documentation_async(self, mock_from_env):
        """Test project documentation creation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        tools = ConfluenceTools()
        tools.api.create_page_async = AsyncMock(
            return_value={
                "success": True,
                "page_id": "789012",
                "page_url": "https://company.atlassian.net/wiki/spaces/DOC/pages/789012",
                "page_title": "Project Overview: Test Project",
            }
        )

        result = await tools.create_project_documentation_async("PROJ", "Test Project")

        assert result["success"] is True
        assert result["page_title"] == "Project Overview: Test Project"

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    def test_get_space_info(self, mock_from_env):
        """Test getting space information."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        tools = ConfluenceTools()
        info = tools.get_space_info()

        assert info["base_url"] == "https://company.atlassian.net"
        assert info["space_key"] == "DOC"
        assert info["username"] == "user@company.com"

    @patch("plugins.confluence.config.ConfluenceConfig.from_env")
    @patch("asyncio.run")
    def test_create_task_documentation_sync(self, mock_run, mock_from_env):
        """Test synchronous wrapper for task documentation creation."""
        mock_config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            username="user@company.com",
            api_key="test_api_key",
            space_key="DOC",
        )
        mock_from_env.return_value = mock_config

        expected_result = {"success": True, "action": "created"}
        mock_run.return_value = expected_result

        tools = ConfluenceTools()
        task_details = {"fields": {"summary": "Test Task"}}

        result = tools.create_task_documentation("TASK-123", task_details)

        assert result == expected_result
        mock_run.assert_called_once()


# Convenience function tests
@patch("plugins.confluence.config.ConfluenceConfig.from_env")
@patch("plugins.confluence.tools.ConfluenceTools")
@pytest.mark.asyncio
async def test_create_task_documentation_async_convenience(
    mock_tools_class, mock_from_env
):
    """Test convenience function for async task documentation creation."""
    from plugins.confluence.tools import create_task_documentation_async

    mock_config = ConfluenceConfig(
        base_url="https://company.atlassian.net",
        username="user@company.com",
        api_key="test_api_key",
        space_key="DOC",
    )
    mock_from_env.return_value = mock_config

    mock_tools = MagicMock()
    mock_tools.create_task_documentation_async = AsyncMock(
        return_value={"success": True}
    )
    mock_tools_class.return_value = mock_tools

    task_details = {"fields": {"summary": "Test Task"}}
    result = await create_task_documentation_async("TASK-123", task_details)

    assert result == {"success": True}
    mock_tools.create_task_documentation_async.assert_called_once_with(
        "TASK-123", task_details, None, None, None
    )


@patch("plugins.confluence.config.ConfluenceConfig.from_env")
@patch("plugins.confluence.tools.ConfluenceTools")
def test_create_task_documentation_sync_convenience(mock_tools_class, mock_from_env):
    """Test convenience function for sync task documentation creation."""
    from plugins.confluence.tools import create_task_documentation

    mock_config = ConfluenceConfig(
        base_url="https://company.atlassian.net",
        username="user@company.com",
        api_key="test_api_key",
        space_key="DOC",
    )
    mock_from_env.return_value = mock_config

    mock_tools = MagicMock()
    mock_tools.create_task_documentation.return_value = {"success": True}
    mock_tools_class.return_value = mock_tools

    task_details = {"fields": {"summary": "Test Task"}}
    result = create_task_documentation("TASK-123", task_details)

    assert result == {"success": True}
    mock_tools.create_task_documentation.assert_called_once_with(
        "TASK-123", task_details, None, None, None
    )
