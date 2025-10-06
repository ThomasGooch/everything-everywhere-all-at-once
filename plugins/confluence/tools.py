"""Confluence tools for documentation workflow integration."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .api import ConfluenceAPI

logger = logging.getLogger(__name__)


class ConfluenceTools:
    """High-level Confluence documentation tools."""

    def __init__(self) -> None:
        """Initialize Confluence tools."""
        self.api = ConfluenceAPI()

    async def create_task_documentation_async(
        self,
        task_id: str,
        task_details: Dict[str, Any],
        pr_url: Optional[str] = None,
        completion_notes: Optional[str] = None,
        space_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create comprehensive documentation for a completed task.

        Args:
            task_id: Task identifier
            task_details: Task details from Jira
            pr_url: Pull request URL
            completion_notes: Additional completion notes
            space_key: Confluence space key (optional)

        Returns:
            Result dictionary with documentation information
        """
        try:
            # Generate page title and content
            fields = task_details.get("fields", {})
            summary = fields.get("summary", "Task")
            page_title = f"{task_id}: {summary}"

            # Generate documentation content
            content = self.api.generate_task_documentation(
                task_id, task_details, pr_url, completion_notes
            )

            # Check if page already exists
            existing_page = await self._find_existing_documentation_async(
                task_id, space_key
            )

            if existing_page:
                # Update existing page
                page_data = existing_page["page"]
                result = await self.api.update_page_async(
                    page_data["id"],
                    page_title,
                    content,
                    page_data["version"]["number"],
                )
                if result["success"]:
                    logger.info(f"Updated documentation for {task_id}")
                    return {
                        "success": True,
                        "action": "updated",
                        "page_id": result["page_id"],
                        "page_url": result["page_url"],
                        "page_title": result["page_title"],
                    }
            else:
                # Create new page
                result = await self.api.create_page_async(
                    page_title, content, space_key
                )
                if result["success"]:
                    logger.info(f"Created documentation for {task_id}")
                    return {
                        "success": True,
                        "action": "created",
                        "page_id": result["page_id"],
                        "page_url": result["page_url"],
                        "page_title": result["page_title"],
                    }

            return result

        except Exception as e:
            logger.error(f"Failed to create task documentation: {e}")
            return {"success": False, "error": str(e)}

    def create_task_documentation(
        self,
        task_id: str,
        task_details: Dict[str, Any],
        pr_url: Optional[str] = None,
        completion_notes: Optional[str] = None,
        space_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for create_task_documentation_async."""
        import asyncio

        return asyncio.run(
            self.create_task_documentation_async(
                task_id, task_details, pr_url, completion_notes, space_key
            )
        )

    async def _find_existing_documentation_async(
        self, task_id: str, space_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find existing documentation page for a task.

        Args:
            task_id: Task identifier
            space_key: Confluence space key (optional)

        Returns:
            Existing page data if found, None otherwise
        """
        try:
            # Search for pages with task ID in title
            space_clause = (
                f"space = {space_key}"
                if space_key
                else f"space = {self.api.config.space_key}"
            )
            cql = f'title ~ "{task_id}" AND {space_clause}'

            search_result = await self.api.search_pages_async(cql, limit=10)

            if search_result["success"] and search_result["results"]:
                # Return the first matching page
                for page in search_result["results"]:
                    if task_id in page["title"]:
                        # Get full page details
                        page_result = await self.api.get_page_async(page["id"])
                        if page_result["success"]:
                            return page_result

            return None

        except Exception as e:
            logger.error(f"Failed to find existing documentation: {e}")
            return None

    async def create_project_documentation_async(
        self,
        project_key: str,
        project_name: str,
        space_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create project overview documentation.

        Args:
            project_key: Project key
            project_name: Project name
            space_key: Confluence space key (optional)

        Returns:
            Result dictionary with project documentation information
        """
        try:
            page_title = f"Project Overview: {project_name}"
            content = f"""
<h1>Project Overview: {project_name}</h1>

<h2>Project Information</h2>
<table>
<tr><th>Project Key</th><td>{project_key}</td></tr>
<tr><th>Project Name</th><td>{project_name}</td></tr>
<tr><th>Last Updated</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
</table>

<h2>Development Automation</h2>
<p>This project uses the AI Development Automation System for streamlined development workflows.</p>

<h3>Automated Workflow Features</h3>
<ul>
<li><strong>Task Management:</strong> Automatic Jira integration and status updates</li>
<li><strong>AI Development:</strong> Claude CLI powered development sessions</li>
<li><strong>Code Quality:</strong> Automated testing, linting, and formatting</li>
<li><strong>Version Control:</strong> Automated GitHub pull request creation</li>
<li><strong>Documentation:</strong> Automatic Confluence documentation generation</li>
</ul>

<h2>Development Process</h2>
<ol>
<li><strong>Task Creation:</strong> Tasks created in Jira with appropriate labels</li>
<li><strong>Automated Pickup:</strong> System monitors for new tasks</li>
<li><strong>Development Session:</strong> Claude CLI session launched in project context</li>
<li><strong>Quality Assurance:</strong> Automated testing and quality gates</li>
<li><strong>Code Review:</strong> Pull request created for team review</li>
<li><strong>Documentation:</strong> Task documentation automatically generated</li>
</ol>

<h2>Task Documentation</h2>
<p>Individual task documentation is automatically generated in this space. Use the search function to find documentation for specific tasks.</p>

<hr/>
<p><em>🤖 This documentation was automatically generated by the AI Development Automation System</em></p>
"""

            result = await self.api.create_page_async(page_title, content, space_key)

            if result["success"]:
                logger.info(f"Created project documentation for {project_name}")

            return result

        except Exception as e:
            logger.error(f"Failed to create project documentation: {e}")
            return {"success": False, "error": str(e)}

    def create_project_documentation(
        self,
        project_key: str,
        project_name: str,
        space_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for create_project_documentation_async."""
        import asyncio

        return asyncio.run(
            self.create_project_documentation_async(
                project_key, project_name, space_key
            )
        )

    def get_space_info(self) -> Dict[str, Any]:
        """Get information about the configured Confluence space.

        Returns:
            Space configuration details
        """
        return {
            "base_url": self.api.config.base_url,
            "space_key": self.api.config.space_key,
            "username": self.api.config.username,
        }


# Convenience functions for direct usage
async def create_task_documentation_async(
    task_id: str,
    task_details: Dict[str, Any],
    pr_url: Optional[str] = None,
    completion_notes: Optional[str] = None,
    space_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function to create task documentation."""
    tools = ConfluenceTools()
    return await tools.create_task_documentation_async(
        task_id, task_details, pr_url, completion_notes, space_key
    )


def create_task_documentation(
    task_id: str,
    task_details: Dict[str, Any],
    pr_url: Optional[str] = None,
    completion_notes: Optional[str] = None,
    space_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous convenience function to create task documentation."""
    tools = ConfluenceTools()
    return tools.create_task_documentation(
        task_id, task_details, pr_url, completion_notes, space_key
    )
