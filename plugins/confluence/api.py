"""Confluence API wrapper for documentation generation."""

import base64
import logging
from typing import Any, Dict, Optional

import aiohttp

from .config import ConfluenceConfig

logger = logging.getLogger(__name__)


class ConfluenceAPI:
    """Confluence API wrapper for autonomous documentation generation."""

    config: ConfluenceConfig

    def __init__(self) -> None:
        """Initialize Confluence API wrapper."""
        config = ConfluenceConfig.from_env()
        if not config:
            raise ValueError(
                "Confluence configuration not available in environment variables"
            )
        self.config = config  # Now MyPy knows this is not None

        # Create auth header
        auth_string = f"{self.config.username}:{self.config.api_key}"
        auth_bytes = auth_string.encode("ascii")
        self.auth_header = base64.b64encode(auth_bytes).decode("ascii")

    async def create_page_async(
        self,
        title: str,
        content: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Confluence page.

        Args:
            title: Page title
            content: Page content in Confluence storage format
            space_key: Space key (defaults to configured space)
            parent_id: Parent page ID (optional)

        Returns:
            Result dictionary with page information
        """
        if not space_key:
            space_key = self.config.space_key

        url = f"{self.config.base_url}/wiki/rest/api/content"
        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

        page_data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": content, "representation": "storage"}},
        }

        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=page_data
                ) as response:
                    if response.status == 200:
                        page_info = await response.json()
                        logger.info(f"Created Confluence page: {title}")
                        return {
                            "success": True,
                            "page_id": page_info["id"],
                            "page_title": page_info["title"],
                            "page_url": f"{self.config.base_url}/wiki{page_info['_links']['webui']}",
                            "page_data": page_info,
                        }
                    else:
                        error_data = await response.json()
                        logger.error(
                            f"Failed to create page: {response.status} - {error_data}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to create Confluence page: {e}")
            return {"success": False, "error": str(e)}

    def create_page(
        self,
        title: str,
        content: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for create_page_async."""
        import asyncio

        return asyncio.run(self.create_page_async(title, content, space_key, parent_id))

    async def update_page_async(
        self, page_id: str, title: str, content: str, version: int
    ) -> Dict[str, Any]:
        """Update an existing Confluence page.

        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content in Confluence storage format
            version: Current version number (must increment)

        Returns:
            Result dictionary with updated page information
        """
        url = f"{self.config.base_url}/wiki/rest/api/content/{page_id}"
        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

        page_data = {
            "version": {"number": version + 1},
            "title": title,
            "type": "page",
            "body": {"storage": {"value": content, "representation": "storage"}},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    url, headers=headers, json=page_data
                ) as response:
                    if response.status == 200:
                        page_info = await response.json()
                        logger.info(f"Updated Confluence page: {title}")
                        return {
                            "success": True,
                            "page_id": page_info["id"],
                            "page_title": page_info["title"],
                            "page_url": f"{self.config.base_url}/wiki{page_info['_links']['webui']}",
                            "page_data": page_info,
                        }
                    else:
                        error_data = await response.json()
                        logger.error(
                            f"Failed to update page: {response.status} - {error_data}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to update Confluence page: {e}")
            return {"success": False, "error": str(e)}

    def update_page(
        self, page_id: str, title: str, content: str, version: int
    ) -> Dict[str, Any]:
        """Synchronous wrapper for update_page_async."""
        import asyncio

        return asyncio.run(self.update_page_async(page_id, title, content, version))

    async def search_pages_async(self, cql: str, limit: int = 25) -> Dict[str, Any]:
        """Search for pages using CQL (Confluence Query Language).

        Args:
            cql: CQL query string
            limit: Maximum number of results

        Returns:
            Search results dictionary
        """
        url = f"{self.config.base_url}/wiki/rest/api/content/search"
        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

        params = {"cql": cql, "limit": limit}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        search_results = await response.json()
                        logger.info(f"Found {len(search_results['results'])} pages")
                        return {
                            "success": True,
                            "results": search_results["results"],
                            "total": search_results["size"],
                        }
                    else:
                        error_data = await response.json()
                        logger.error(
                            f"Failed to search pages: {response.status} - {error_data}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to search Confluence pages: {e}")
            return {"success": False, "error": str(e)}

    def search_pages(self, cql: str, limit: int = 25) -> Dict[str, Any]:
        """Synchronous wrapper for search_pages_async."""
        import asyncio

        return asyncio.run(self.search_pages_async(cql, limit))

    async def get_page_async(self, page_id: str) -> Dict[str, Any]:
        """Get page information by ID.

        Args:
            page_id: Page ID

        Returns:
            Page information dictionary
        """
        url = f"{self.config.base_url}/wiki/rest/api/content/{page_id}"
        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

        params = {"expand": "body.storage,version,space"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        page_data = await response.json()
                        return {"success": True, "page": page_data}
                    else:
                        error_data = await response.json()
                        logger.error(
                            f"Failed to get page: {response.status} - {error_data}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to get Confluence page: {e}")
            return {"success": False, "error": str(e)}

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for get_page_async."""
        import asyncio

        return asyncio.run(self.get_page_async(page_id))

    def generate_task_documentation(
        self,
        task_id: str,
        task_details: Dict[str, Any],
        pr_url: Optional[str] = None,
        completion_notes: Optional[str] = None,
    ) -> str:
        """Generate Confluence documentation content for a completed task.

        Args:
            task_id: Task identifier
            task_details: Task details from Jira
            pr_url: Pull request URL
            completion_notes: Additional completion notes

        Returns:
            Confluence storage format content
        """
        fields = task_details.get("fields", {})
        summary = fields.get("summary", "Task")
        description = fields.get("description", "No description available")
        status = fields.get("status", {}).get("name", "Unknown")
        assignee = fields.get("assignee", {})
        assignee_name = (
            assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
        )

        content = f"""
<h1>Task Documentation: {task_id}</h1>

<h2>Overview</h2>
<table>
<tr><th>Task ID</th><td>{task_id}</td></tr>
<tr><th>Summary</th><td>{summary}</td></tr>
<tr><th>Status</th><td><strong>{status}</strong></td></tr>
<tr><th>Assignee</th><td>{assignee_name}</td></tr>
</table>

<h2>Description</h2>
<p>{description}</p>

<h2>Implementation Details</h2>
<p>This task was completed using the AI Development Automation System, which provides end-to-end automation from Jira task management through GitHub workflow completion.</p>

<h3>Development Process</h3>
<ol>
<li><strong>Task Assignment:</strong> Task automatically picked up from Jira</li>
<li><strong>Development Environment:</strong> Repository cloned and feature branch created</li>
<li><strong>AI-Powered Development:</strong> Implementation completed using Claude CLI</li>
<li><strong>Quality Assurance:</strong> Code automatically formatted, tested, and linted</li>
<li><strong>Version Control:</strong> Changes committed and pushed to feature branch</li>
<li><strong>Code Review:</strong> Pull request created for team review</li>
<li><strong>Documentation:</strong> This page automatically generated</li>
</ol>
"""

        if pr_url:
            content += f"""
<h3>Pull Request</h3>
<p>Code changes are available for review: <a href="{pr_url}">{pr_url}</a></p>
"""

        if completion_notes:
            content += f"""
<h3>Completion Notes</h3>
<p>{completion_notes}</p>
"""

        content += f"""
<h2>Technical Details</h2>
<p><strong>Automation System:</strong> AI Development Automation System</p>
<p><strong>Development Tools:</strong> Claude CLI, GitHub Actions, Jira API</p>
<p><strong>Quality Gates:</strong> Automated testing, linting, formatting, and security scanning</p>

<h2>Related Resources</h2>
<ul>
<li><a href="{task_details.get('self', '#')}">Jira Task</a></li>
"""

        if pr_url:
            content += f'<li><a href="{pr_url}">Pull Request</a></li>'

        content += """
</ul>

<hr/>
<p><em>🤖 This documentation was automatically generated by the AI Development Automation System</em></p>
"""

        return content.strip()
