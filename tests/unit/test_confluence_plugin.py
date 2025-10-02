"""Unit tests for Confluence Plugin"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_interface import PluginResult, PluginStatus, PluginType
from plugins.confluence_plugin import ConfluencePlugin


@pytest.mark.integration
class TestConfluencePlugin:
    """Test Confluence plugin features"""

    @pytest.fixture
    def confluence_config(self):
        """Confluence configuration for testing"""
        return {
            "connection": {
                "url": "https://test.atlassian.net/wiki",
                "email": "test@example.com",
                "api_token": "test-token",
            },
            "options": {
                "timeout": 30,
                "default_space": "TEST",
                "page_templates": {
                    "api_documentation": "api_doc_template.html",
                    "user_guide": "user_guide_template.html",
                    "meeting_notes": "meeting_notes_template.html",
                },
                "auto_labels": {"ai_generated": True, "version_controlled": True},
            },
        }

    @pytest.fixture
    def confluence_plugin(self, confluence_config):
        """Create Confluence plugin instance"""
        return ConfluencePlugin(confluence_config)

    # RED: Test basic plugin initialization
    def test_confluence_plugin_initialization(self, confluence_plugin):
        """Test that plugin initializes correctly"""
        assert confluence_plugin.plugin_type == PluginType.DOCUMENTATION
        assert confluence_plugin.name == "confluence"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, confluence_plugin):
        """Test health check when service is healthy"""

        # Set up plugin state to simulate successful initialization
        confluence_plugin._is_initialized = True
        confluence_plugin._connection_established = True
        confluence_plugin._session = MagicMock()

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_session.get.return_value.__aenter__.return_value = mock_response

            status = await confluence_plugin.health_check()
            assert status == PluginStatus.HEALTHY

    # RED: Test for create_page
    @pytest.mark.asyncio
    async def test_create_page(self, confluence_plugin):
        """Test creating a new Confluence page"""

        page_data = {
            "space_key": "TEST",
            "title": "Test Documentation",
            "content": "<h1>Test Content</h1><p>This is test documentation.</p>",
            "parent_page_id": "123456",
            "labels": ["api", "documentation"],
        }

        # Set up plugin state
        confluence_plugin._base_url = "https://test.atlassian.net/wiki"

        with patch.object(confluence_plugin, "_session") as mock_session, patch.object(
            confluence_plugin, "add_page_labels"
        ) as mock_add_labels:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "id": "789012",
                    "title": "Test Documentation",
                    "version": {"number": 1},
                    "_links": {"webui": "/pages/789012"},
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_add_labels.return_value = PluginResult(
                success=True, data={"labels": ["api", "documentation"]}
            )

            result = await confluence_plugin.create_page_enhanced(page_data)

            assert result.success
            assert result.data["page_id"] == "789012"
            assert result.data["page_url"].endswith("/pages/789012")

    # RED: Test for update_page
    @pytest.mark.asyncio
    async def test_update_page(self, confluence_plugin):
        """Test updating an existing Confluence page"""

        update_data = {
            "page_id": "789012",
            "title": "Updated Test Documentation",
            "content": "<h1>Updated Content</h1><p>This is updated test documentation.</p>",
            "version": 1,
        }

        # Set up plugin state
        confluence_plugin._base_url = "https://test.atlassian.net/wiki"

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "id": "789012",
                    "title": "Updated Test Documentation",
                    "version": {"number": 2},
                    "_links": {"webui": "/pages/789012"},
                }
            )
            mock_session.put.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.update_page_enhanced(update_data)

            assert result.success
            assert result.data["page_id"] == "789012"
            assert result.data["version"] == 2

    # RED: Test for search_pages
    @pytest.mark.asyncio
    async def test_search_pages(self, confluence_plugin):
        """Test searching for pages"""

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "123",
                            "title": "API Documentation",
                            "excerpt": "Documentation for our API",
                            "_links": {"webui": "/pages/123"},
                        },
                        {
                            "id": "456",
                            "title": "User Guide",
                            "excerpt": "Guide for end users",
                            "_links": {"webui": "/pages/456"},
                        },
                    ],
                    "size": 2,
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.search_pages("API", space_key="TEST")

            assert result.success
            assert len(result.data["pages"]) == 2
            assert result.data["total_count"] == 2

    # RED: Test for create_page_from_template
    @pytest.mark.asyncio
    async def test_create_page_from_template(self, confluence_plugin):
        """Test creating page using a template"""

        template_data = {
            "template_type": "api_documentation",
            "space_key": "TEST",
            "title": "New API Docs",
            "variables": {
                "api_name": "User Management API",
                "version": "v2.0",
                "endpoints": ["GET /users", "POST /users"],
            },
        }

        with patch.object(
            confluence_plugin, "create_page_enhanced"
        ) as mock_create_page:
            mock_create_page.return_value = PluginResult(
                success=True,
                data={
                    "page_id": "999888",
                    "page_url": "https://test.atlassian.net/pages/999888",
                    "title": "New API Docs",
                    "version": 1,
                },
            )

            result = await confluence_plugin.create_page_from_template(template_data)

            assert result.success
            assert result.data["page_id"] == "999888"

    # RED: Test for add_page_labels
    @pytest.mark.asyncio
    async def test_add_page_labels(self, confluence_plugin):
        """Test adding labels to a page"""

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {"name": "api"},
                        {"name": "documentation"},
                        {"name": "v2"},
                    ]
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.add_page_labels(
                "789012", ["api", "documentation", "v2"]
            )

            assert result.success
            assert len(result.data["labels"]) == 3

    # RED: Test for get_page_attachments
    @pytest.mark.asyncio
    async def test_get_page_attachments(self, confluence_plugin):
        """Test getting page attachments"""

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "att123",
                            "title": "diagram.png",
                            "metadata": {"mediaType": "image/png"},
                            "_links": {"download": "/download/att123"},
                        }
                    ]
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.get_page_attachments("789012")

            assert result.success
            assert len(result.data["attachments"]) == 1
            assert result.data["attachments"][0]["title"] == "diagram.png"

    # RED: Test for upload_attachment
    @pytest.mark.asyncio
    async def test_upload_attachment(self, confluence_plugin):
        """Test uploading an attachment to a page"""

        with patch.object(confluence_plugin, "_session") as mock_session, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("builtins.open", MagicMock()) as mock_open:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "att456",
                            "title": "new_diagram.png",
                            "_links": {"download": "/download/att456"},
                        }
                    ]
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.upload_attachment(
                page_id="789012",
                file_path="/tmp/diagram.png",
                filename="new_diagram.png",
            )

            assert result.success
            assert result.data["attachment_id"] == "att456"

    # RED: Test for create_space
    @pytest.mark.asyncio
    async def test_create_space(self, confluence_plugin):
        """Test creating a new space"""

        space_data = {
            "key": "NEWSPACE",
            "name": "New Project Space",
            "description": "Space for the new project",
        }

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "id": "space123",
                    "key": "NEWSPACE",
                    "name": "New Project Space",
                    "_links": {"webui": "/spaces/NEWSPACE"},
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.create_space(space_data)

            assert result.success
            assert result.data["space_key"] == "NEWSPACE"
            assert result.data["space_id"] == "space123"

    # RED: Test for get_page_history
    @pytest.mark.asyncio
    async def test_get_page_history(self, confluence_plugin):
        """Test getting page version history"""

        with patch.object(confluence_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "results": [
                        {
                            "number": 2,
                            "when": "2024-12-01T10:00:00Z",
                            "by": {"displayName": "Test User"},
                        },
                        {
                            "number": 1,
                            "when": "2024-11-30T15:30:00Z",
                            "by": {"displayName": "Another User"},
                        },
                    ]
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await confluence_plugin.get_page_history("789012")

            assert result.success
            assert len(result.data["versions"]) == 2
            assert result.data["versions"][0]["number"] == 2
