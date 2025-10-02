"""Confluence plugin implementation for documentation management"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession

from core.plugin_interface import (
    DocumentationPlugin,
    PluginResult,
    PluginStatus,
    PluginType,
    PluginValidationError,
)

logger = logging.getLogger(__name__)

# Constants for HTTP status codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404


class ConfluencePlugin(DocumentationPlugin):
    """Confluence documentation plugin for managing wiki pages and spaces"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Confluence plugin

        Args:
            config: Configuration dictionary containing connection details
        """
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._base_url = ""
        self.name = "confluence"

    @property
    def plugin_type(self) -> PluginType:
        """Return the plugin type"""
        return PluginType.DOCUMENTATION

    def get_plugin_type(self) -> PluginType:
        """Return the plugin type"""
        return PluginType.DOCUMENTATION

    def get_plugin_name(self) -> str:
        """Return the specific plugin name"""
        return "confluence"

    def get_version(self) -> str:
        """Return plugin version"""
        return "1.0.0"

    def validate_config(self) -> bool:
        """Validate plugin configuration

        Returns:
            True if configuration is valid, False otherwise

        Raises:
            PluginValidationError: If configuration is invalid
        """
        try:
            required_fields = ["connection"]
            for field in required_fields:
                if field not in self.config:
                    raise PluginValidationError(
                        f"Missing required config field: {field}"
                    )

            connection = self.config["connection"]
            required_connection_fields = ["url", "email", "api_token"]
            for field in required_connection_fields:
                if field not in connection:
                    raise PluginValidationError(
                        f"Missing required connection field: {field}"
                    )

            return True
        except PluginValidationError:
            raise
        except Exception as e:
            raise PluginValidationError(f"Configuration validation failed: {e}")

    def _validate_config(self) -> None:
        """Internal validation helper - raises exception on failure"""
        self.validate_config()

    def _get_request_headers(self) -> Dict[str, str]:
        """Get HTTP request headers for Confluence API

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Basic {self._get_auth_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_auth_token(self) -> str:
        """Get base64 encoded auth token for basic authentication

        Returns:
            Base64 encoded auth string
        """
        import base64

        email = self.config["connection"]["email"]
        api_token = self.config["connection"]["api_token"]
        auth_string = f"{email}:{api_token}"
        return base64.b64encode(auth_string.encode()).decode()

    def _get_api_url(self, endpoint: str = "") -> str:
        """Construct full API URL

        Args:
            endpoint: API endpoint path

        Returns:
            Complete API URL
        """
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return f"{self._base_url}/rest/api/{endpoint}"

    async def initialize(self) -> bool:
        """Initialize the plugin and establish connection

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Confluence plugin")

            # Validate configuration
            self._validate_config()

            # Set up base URL
            self._base_url = self.config["connection"]["url"].rstrip("/")

            # Create aiohttp session
            timeout = aiohttp.ClientTimeout(
                total=self.config.get("options", {}).get("timeout", 30)
            )
            self._session = ClientSession(
                timeout=timeout, connector=aiohttp.TCPConnector(limit=10)
            )

            # Test connection
            async with self._session.get(
                self._get_api_url("user/current"), headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    self._is_initialized = True
                    self._connection_established = True
                    logger.info("Confluence plugin initialized successfully")
                    return True
                else:
                    logger.error(
                        f"Confluence connection test failed with status {response.status}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to initialize Confluence plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """Clean up plugin resources

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info("Cleaning up Confluence plugin")

            if self._session:
                await self._session.close()
                self._session = None

            self._is_initialized = False
            self._connection_established = False

            logger.info("Confluence plugin cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during Confluence plugin cleanup: {e}")
            return False

    async def health_check(self) -> PluginStatus:
        """Check plugin health status

        Returns:
            Current health status
        """
        if (
            not self._is_initialized
            or not self._connection_established
            or not self._session
        ):
            return PluginStatus.UNHEALTHY

        try:
            # Simple health check - get current user info
            async with self._session.get(
                self._get_api_url("user/current"), headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    return PluginStatus.HEALTHY
                else:
                    logger.warning(
                        f"Confluence health check returned status {response.status}"
                    )
                    return PluginStatus.DEGRADED

        except Exception as e:
            logger.error(f"Confluence health check failed: {e}")
            return PluginStatus.UNHEALTHY

    # Implementation of abstract methods from DocumentationPlugin
    async def create_page(self, space: str, title: str, content: str) -> PluginResult:
        """Create documentation page - basic interface implementation

        Args:
            space: Confluence space key
            title: Page title
            content: Page content (HTML format)

        Returns:
            PluginResult with page ID
        """
        page_data = {"space_key": space, "title": title, "content": content}
        return await self.create_page_enhanced(page_data)

    async def update_page(self, page_id: str, content: str) -> PluginResult:
        """Update existing page - basic interface implementation

        Args:
            page_id: Page identifier
            content: Updated content (HTML format)

        Returns:
            PluginResult indicating success/failure
        """
        # First get current page to get version number
        current_page_result = await self.get_page(page_id)
        if not current_page_result.success:
            return current_page_result

        current_version = current_page_result.data["version"]

        update_data = {
            "page_id": page_id,
            "content": content,
            "version": current_version,
        }
        return await self.update_page_enhanced(update_data)

    # Enhanced Confluence-specific methods
    async def create_page_enhanced(self, page_data: Dict[str, Any]) -> PluginResult:
        """Create a new Confluence page with enhanced options

        Args:
            page_data: Dictionary containing page information:
                - space_key: Confluence space key
                - title: Page title
                - content: Page content in HTML format
                - parent_page_id: Optional parent page ID
                - labels: Optional list of labels to add

        Returns:
            PluginResult with created page information
        """
        try:
            # Build page creation payload
            payload = {
                "type": "page",
                "title": page_data["title"],
                "space": {"key": page_data["space_key"]},
                "body": {
                    "storage": {
                        "value": page_data["content"],
                        "representation": "storage",
                    }
                },
            }

            # Add parent page if specified
            if "parent_page_id" in page_data:
                payload["ancestors"] = [{"id": page_data["parent_page_id"]}]

            async with self._session.post(
                self._get_api_url("content"),
                headers=self._get_request_headers(),
                data=json.dumps(payload),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()
                    page_id = response_data["id"]

                    # Add labels if specified
                    if "labels" in page_data and page_data["labels"]:
                        await self.add_page_labels(page_id, page_data["labels"])

                    # Add auto-labels from config
                    auto_labels = self.config.get("options", {}).get("auto_labels", {})
                    if auto_labels.get("ai_generated"):
                        await self.add_page_labels(page_id, ["ai-generated"])

                    base_url = self._base_url.replace("/wiki", "")
                    page_url = f"{base_url}{response_data['_links']['webui']}"

                    return PluginResult(
                        success=True,
                        data={
                            "page_id": page_id,
                            "page_url": page_url,
                            "title": response_data["title"],
                            "version": response_data["version"]["number"],
                        },
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to create page: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to create page: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return PluginResult(success=False, error=str(e))

    async def update_page_enhanced(self, update_data: Dict[str, Any]) -> PluginResult:
        """Update an existing Confluence page

        Args:
            update_data: Dictionary containing update information:
                - page_id: Page ID to update
                - title: Optional new title
                - content: New page content
                - version: Current page version number

        Returns:
            PluginResult with updated page information
        """
        try:
            payload = {
                "version": {"number": update_data["version"] + 1},
                "type": "page",
                "body": {
                    "storage": {
                        "value": update_data["content"],
                        "representation": "storage",
                    }
                },
            }

            if "title" in update_data:
                payload["title"] = update_data["title"]

            async with self._session.put(
                self._get_api_url(f"content/{update_data['page_id']}"),
                headers=self._get_request_headers(),
                data=json.dumps(payload),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()
                    base_url = self._base_url.replace("/wiki", "")
                    page_url = f"{base_url}{response_data['_links']['webui']}"

                    return PluginResult(
                        success=True,
                        data={
                            "page_id": response_data["id"],
                            "page_url": page_url,
                            "title": response_data["title"],
                            "version": response_data["version"]["number"],
                        },
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to update page: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to update page: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error updating page: {e}")
            return PluginResult(success=False, error=str(e))

    async def get_page(
        self, page_id: str, expand: Optional[List[str]] = None
    ) -> PluginResult:
        """Get page information

        Args:
            page_id: Page ID to retrieve
            expand: Optional list of fields to expand

        Returns:
            PluginResult with page information
        """
        try:
            expand_params = expand or ["body.storage", "version", "space"]
            expand_str = ",".join(expand_params)

            async with self._session.get(
                self._get_api_url(f"content/{page_id}?expand={expand_str}"),
                headers=self._get_request_headers(),
            ) as response:
                if response.status == HTTP_OK:
                    page_data = await response.json()

                    return PluginResult(
                        success=True,
                        data={
                            "page_id": page_data["id"],
                            "title": page_data["title"],
                            "content": page_data.get("body", {})
                            .get("storage", {})
                            .get("value", ""),
                            "version": page_data["version"]["number"],
                            "space_key": page_data["space"]["key"],
                            "created": page_data.get("history", {}).get("createdDate"),
                            "last_modified": page_data["version"]["when"],
                        },
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to get page: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to get page: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error getting page: {e}")
            return PluginResult(success=False, error=str(e))

    async def search_pages(
        self, query: str, space_key: Optional[str] = None, limit: int = 10
    ) -> PluginResult:
        """Search for pages in Confluence

        Args:
            query: Search query string
            space_key: Optional space to limit search to
            limit: Maximum number of results to return

        Returns:
            PluginResult with search results
        """
        try:
            # Build CQL (Confluence Query Language) query
            cql_query = f'text ~ "{query}"'
            if space_key:
                cql_query += f' and space = "{space_key}"'

            cql_query += " and type = page"

            async with self._session.get(
                self._get_api_url(
                    f"content/search?cql={cql_query}&limit={limit}&expand=excerpt"
                ),
                headers=self._get_request_headers(),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()

                    pages = []
                    for result in response_data.get("results", []):
                        base_url = self._base_url.replace("/wiki", "")
                        page_url = f"{base_url}{result['_links']['webui']}"

                        pages.append(
                            {
                                "page_id": result["id"],
                                "title": result["title"],
                                "excerpt": result.get("excerpt", ""),
                                "page_url": page_url,
                                "space_key": result.get("space", {}).get("key", ""),
                            }
                        )

                    return PluginResult(
                        success=True,
                        data={
                            "pages": pages,
                            "total_count": response_data.get("size", len(pages)),
                        },
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to search pages: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to search pages: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error searching pages: {e}")
            return PluginResult(success=False, error=str(e))

    async def create_page_from_template(
        self, template_data: Dict[str, Any]
    ) -> PluginResult:
        """Create a page using a predefined template

        Args:
            template_data: Dictionary containing template information:
                - template_type: Type of template to use
                - space_key: Confluence space key
                - title: Page title
                - variables: Dictionary of template variables

        Returns:
            PluginResult with created page information
        """
        try:
            template_content = self._render_template(
                template_data["template_type"], template_data.get("variables", {})
            )

            page_data = {
                "space_key": template_data["space_key"],
                "title": template_data["title"],
                "content": template_content,
                "labels": ["template-generated"],
            }

            # Add parent if specified
            if "parent_page_id" in template_data:
                page_data["parent_page_id"] = template_data["parent_page_id"]

            return await self.create_page_enhanced(page_data)

        except Exception as e:
            logger.error(f"Error creating page from template: {e}")
            return PluginResult(success=False, error=str(e))

    def _render_template(self, template_type: str, variables: Dict[str, Any]) -> str:
        """Render a template with provided variables

        Args:
            template_type: Type of template to render
            variables: Template variables

        Returns:
            Rendered template content
        """
        templates = {
            "api_documentation": self._get_api_doc_template(),
            "user_guide": self._get_user_guide_template(),
            "meeting_notes": self._get_meeting_notes_template(),
        }

        template = templates.get(
            template_type, "<h1>{{title}}</h1><p>Template not found</p>"
        )

        # Simple template variable substitution
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            template = template.replace(placeholder, str(value))

        return template

    def _get_api_doc_template(self) -> str:
        """Get API documentation template"""
        return """
        <h1>{{api_name}} Documentation</h1>
        <h2>Version: {{version}}</h2>
        <h3>Endpoints</h3>
        <ul>
        {% for endpoint in endpoints %}
            <li><code>{{endpoint}}</code></li>
        {% endfor %}
        </ul>
        <h3>Authentication</h3>
        <p>This API uses standard authentication methods.</p>
        <h3>Examples</h3>
        <p>Coming soon...</p>
        """

    def _get_user_guide_template(self) -> str:
        """Get user guide template"""
        return """
        <h1>{{guide_title}} User Guide</h1>
        <h2>Overview</h2>
        <p>{{overview}}</p>
        <h2>Getting Started</h2>
        <ol>
            <li>Step 1: {{step1}}</li>
            <li>Step 2: {{step2}}</li>
            <li>Step 3: {{step3}}</li>
        </ol>
        <h2>Advanced Features</h2>
        <p>{{advanced_features}}</p>
        """

    def _get_meeting_notes_template(self) -> str:
        """Get meeting notes template"""
        return """
        <h1>Meeting Notes - {{meeting_title}}</h1>
        <p><strong>Date:</strong> {{date}}</p>
        <p><strong>Attendees:</strong> {{attendees}}</p>
        <h2>Agenda</h2>
        <ul>
        {% for item in agenda_items %}
            <li>{{item}}</li>
        {% endfor %}
        </ul>
        <h2>Discussion Points</h2>
        <p>{{discussion}}</p>
        <h2>Action Items</h2>
        <ul>
        {% for action in action_items %}
            <li>{{action}}</li>
        {% endfor %}
        </ul>
        """

    async def add_page_labels(self, page_id: str, labels: List[str]) -> PluginResult:
        """Add labels to a page

        Args:
            page_id: Page ID to add labels to
            labels: List of label names to add

        Returns:
            PluginResult with added labels information
        """
        try:
            # Confluence expects labels in a specific format
            label_objects = [{"name": label} for label in labels]

            async with self._session.post(
                self._get_api_url(f"content/{page_id}/label"),
                headers=self._get_request_headers(),
                data=json.dumps(label_objects),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()

                    added_labels = [
                        result["name"] for result in response_data.get("results", [])
                    ]

                    return PluginResult(
                        success=True, data={"labels": added_labels, "page_id": page_id}
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to add labels: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to add labels: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return PluginResult(success=False, error=str(e))

    async def get_page_attachments(self, page_id: str) -> PluginResult:
        """Get attachments for a page

        Args:
            page_id: Page ID to get attachments for

        Returns:
            PluginResult with attachment information
        """
        try:
            async with self._session.get(
                self._get_api_url(
                    f"content/{page_id}/child/attachment?expand=download"
                ),
                headers=self._get_request_headers(),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()

                    attachments = []
                    for result in response_data.get("results", []):
                        attachments.append(
                            {
                                "attachment_id": result["id"],
                                "title": result["title"],
                                "media_type": result.get("metadata", {}).get(
                                    "mediaType", ""
                                ),
                                "file_size": result.get("extensions", {}).get(
                                    "fileSize", 0
                                ),
                                "download_url": result["_links"]["download"],
                            }
                        )

                    return PluginResult(
                        success=True,
                        data={"attachments": attachments, "page_id": page_id},
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to get attachments: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to get attachments: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error getting attachments: {e}")
            return PluginResult(success=False, error=str(e))

    async def upload_attachment(
        self, page_id: str, file_path: str, filename: str
    ) -> PluginResult:
        """Upload an attachment to a page

        Args:
            page_id: Page ID to upload attachment to
            file_path: Local path to the file
            filename: Name to give the uploaded file

        Returns:
            PluginResult with uploaded attachment information
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return PluginResult(
                    success=False, error=f"File does not exist: {file_path}"
                )

            # Note: This is a simplified implementation
            # In a real implementation, you'd use aiofiles and multipart form data
            with open(file_path_obj, "rb") as file:
                data = aiohttp.FormData()
                data.add_field("file", file, filename=filename)

                async with self._session.post(
                    self._get_api_url(f"content/{page_id}/child/attachment"),
                    headers={
                        "Authorization": f"Basic {self._get_auth_token()}"
                    },  # Skip content-type for multipart
                    data=data,
                ) as response:
                    if response.status == HTTP_OK:
                        response_data = await response.json()

                        if response_data.get("results"):
                            attachment = response_data["results"][0]
                            return PluginResult(
                                success=True,
                                data={
                                    "attachment_id": attachment["id"],
                                    "filename": attachment["title"],
                                    "download_url": attachment["_links"]["download"],
                                },
                            )
                        else:
                            return PluginResult(
                                success=False,
                                error="No attachment returned in response",
                            )
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to upload attachment: {response.status} - {error_text}"
                        )
                        return PluginResult(
                            success=False,
                            error=f"Failed to upload attachment: {response.status} - {error_text}",
                        )

        except Exception as e:
            logger.error(f"Error uploading attachment: {e}")
            return PluginResult(success=False, error=str(e))

    async def create_space(self, space_data: Dict[str, Any]) -> PluginResult:
        """Create a new Confluence space

        Args:
            space_data: Dictionary containing space information:
                - key: Space key (unique identifier)
                - name: Space name
                - description: Space description

        Returns:
            PluginResult with created space information
        """
        try:
            payload = {
                "key": space_data["key"],
                "name": space_data["name"],
                "description": {
                    "plain": {
                        "value": space_data.get("description", ""),
                        "representation": "plain",
                    }
                },
            }

            async with self._session.post(
                self._get_api_url("space"),
                headers=self._get_request_headers(),
                data=json.dumps(payload),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()
                    base_url = self._base_url.replace("/wiki", "")
                    space_url = f"{base_url}{response_data['_links']['webui']}"

                    return PluginResult(
                        success=True,
                        data={
                            "space_id": response_data["id"],
                            "space_key": response_data["key"],
                            "space_name": response_data["name"],
                            "space_url": space_url,
                        },
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to create space: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to create space: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error creating space: {e}")
            return PluginResult(success=False, error=str(e))

    async def get_page_history(self, page_id: str, limit: int = 10) -> PluginResult:
        """Get version history for a page

        Args:
            page_id: Page ID to get history for
            limit: Maximum number of versions to return

        Returns:
            PluginResult with version history
        """
        try:
            async with self._session.get(
                self._get_api_url(
                    f"content/{page_id}/history?limit={limit}&expand=by,when"
                ),
                headers=self._get_request_headers(),
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()

                    versions = []
                    for version in response_data.get("results", []):
                        versions.append(
                            {
                                "number": version["number"],
                                "when": version["when"],
                                "by": version.get("by", {}).get(
                                    "displayName", "Unknown"
                                ),
                                "message": version.get("message", ""),
                            }
                        )

                    return PluginResult(
                        success=True, data={"versions": versions, "page_id": page_id}
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to get page history: {response.status} - {error_text}"
                    )
                    return PluginResult(
                        success=False,
                        error=f"Failed to get page history: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error getting page history: {e}")
            return PluginResult(success=False, error=str(e))
