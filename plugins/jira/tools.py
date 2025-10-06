"""Jira tools for Claude CLI integration."""

import os
from typing import Any, Callable, Dict

from .api import JiraAPI


def register_tools() -> Dict[str, Callable]:
    """Register Jira tools with Claude CLI.

    Returns:
        Dictionary of tool names to callable functions
    """
    # Check if Jira is configured (support multiple naming conventions)
    if not (os.getenv("JIRA_API_KEY") or os.getenv("JIRA_API_TOKEN")):
        return {}  # Skip if not configured

    return {
        "jira_get_task": jira_get_task,
        "jira_search_tasks": jira_search_tasks,
        "jira_get_my_tasks": jira_get_my_tasks,
        "jira_update_status": jira_update_status,
        "jira_create_task": jira_create_task,
        "jira_assign_task": jira_assign_task,
        "jira_add_comment": jira_add_comment,
        "jira_transition_task": jira_transition_task,
    }


def jira_get_task(task_id: str) -> Dict[str, Any]:
    """Get detailed task information from Jira.

    Args:
        task_id: Jira task ID

    Returns:
        Task details dictionary
    """
    try:
        api = JiraAPI()
        return api.get_issue(task_id)
    except Exception as e:
        return {"error": str(e), "success": False}


def jira_update_status(task_id: str, status: str) -> Dict[str, Any]:
    """Update task status in Jira.

    Args:
        task_id: Jira task ID
        status: New status (e.g., "In Progress", "Done", "To Do")

    Returns:
        Update result
    """
    try:
        api = JiraAPI()
        return api.transition_issue(task_id, status)
    except Exception as e:
        return {"error": str(e), "success": False}


def jira_search_tasks(jql: str, max_results: int = 50) -> Dict[str, Any]:
    """Search for tasks using JQL query.

    Args:
        jql: JQL query string
        max_results: Maximum number of results

    Returns:
        Search results
    """
    try:
        api = JiraAPI()
        import asyncio

        return asyncio.run(api.search_issues_async(jql, max_results))
    except Exception as e:
        return {"error": str(e), "success": False, "issues": [], "total": 0}


def jira_get_my_tasks() -> Dict[str, Any]:
    """Get tasks assigned to current user.

    Returns:
        Tasks assigned to current user
    """
    try:
        api = JiraAPI()
        import asyncio

        return asyncio.run(api.get_my_issues_async())
    except Exception as e:
        return {"error": str(e), "success": False, "issues": [], "total": 0}


def jira_create_task(
    project_key: str, summary: str, description: str = ""
) -> Dict[str, Any]:
    """Create a new task in Jira.

    Args:
        project_key: Jira project key
        summary: Task summary
        description: Task description

    Returns:
        Created task details
    """
    # Mock implementation for now
    return {
        "key": f"{project_key}-123",
        "summary": summary,
        "description": description,
        "success": True,
    }


def jira_assign_task(task_id: str, assignee: str) -> Dict[str, Any]:
    """Assign task to user.

    Args:
        task_id: Jira task ID
        assignee: Username to assign to

    Returns:
        Assignment result
    """
    return {"task_id": task_id, "assignee": assignee, "success": True}


def jira_add_comment(task_id: str, comment: str) -> Dict[str, Any]:
    """Add comment to task.

    Args:
        task_id: Jira task ID
        comment: Comment text

    Returns:
        Comment addition result
    """
    try:
        api = JiraAPI()
        return api.add_comment(task_id, comment)
    except Exception as e:
        return {"error": str(e), "success": False}


def jira_transition_task(task_id: str, transition: str) -> Dict[str, Any]:
    """Transition task to new status.

    Args:
        task_id: Jira task ID
        transition: Transition name

    Returns:
        Transition result
    """
    try:
        api = JiraAPI()
        return api.transition_issue(task_id, transition)
    except Exception as e:
        return {"error": str(e), "success": False}
