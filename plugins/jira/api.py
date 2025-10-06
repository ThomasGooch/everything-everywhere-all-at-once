"""Direct Jira API wrapper for modular plugin system."""

import asyncio
import base64
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from .config import JiraConfig

logger = logging.getLogger(__name__)


class JiraAPI:
    """Direct Jira API wrapper for autonomous execution."""
    
    def __init__(self):
        """Initialize Jira API wrapper."""
        self.config = JiraConfig.from_env()
        if not self.config:
            raise ValueError("Jira configuration not available in environment variables")
        
        # Create auth header
        auth_string = f"{self.config.username}:{self.config.api_key}"
        auth_bytes = auth_string.encode('ascii')
        self.auth_header = base64.b64encode(auth_bytes).decode('ascii')
    
    def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Get issue details from Jira.
        
        Args:
            issue_id: Jira issue ID
            
        Returns:
            Issue data dictionary
        """
        # Use the async version via asyncio
        import asyncio
        return asyncio.run(self.get_issue_async(issue_id))
    
    async def get_issue_async(self, issue_id: str) -> Dict[str, Any]:
        """Async version of get_issue.
        
        Args:
            issue_id: Jira issue ID
            
        Returns:
            Issue data dictionary
        """
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get issue: {response.status}")
    
    def search_issues(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        """Search issues using JQL.
        
        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            
        Returns:
            Search results dictionary
        """
        # Mock implementation - in production this would make actual API call
        return {
            'issues': [],
            'total': 0,
            'maxResults': max_results
        }
    
    async def search_issues_async(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        """Async version of search_issues.
        
        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            
        Returns:
            Search results dictionary
        """
        url = f"{self.config.base_url}/rest/api/2/search"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'jql': jql,
            'maxResults': max_results,
            'fields': 'key,summary,status,assignee,priority,issuetype,updated,created'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to search issues: {response.status} - {error_text}")
    
    def get_my_issues(self) -> Dict[str, Any]:
        """Get issues assigned to current user.
        
        Returns:
            Issues assigned to current user
        """
        # Use search with JQL for current user
        return self.search_issues('assignee = currentUser() ORDER BY updated DESC')
    
    async def get_my_issues_async(self) -> Dict[str, Any]:
        """Async version of get_my_issues.
        
        Returns:
            Issues assigned to current user
        """
        return await self.search_issues_async('assignee = currentUser() ORDER BY updated DESC')
    
    def add_comment(self, issue_id: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue.
        
        Args:
            issue_id: Jira issue ID
            comment: Comment text
            
        Returns:
            Comment addition result
        """
        # Use the async version via asyncio
        import asyncio
        return asyncio.run(self.add_comment_async(issue_id, comment))
    
    async def add_comment_async(self, issue_id: str, comment: str) -> Dict[str, Any]:
        """Async version of add_comment.
        
        Args:
            issue_id: Jira issue ID
            comment: Comment text
            
        Returns:
            Comment addition result
        """
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}/comment"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'body': comment
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return {
                        'success': True,
                        'comment_id': result.get('id'),
                        'created': result.get('created'),
                        'body': result.get('body')
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"Failed to add comment: {response.status} - {error_text}"
                    }
    
    def transition_issue(self, issue_id: str, status: str) -> Dict[str, Any]:
        """Transition issue to new status.
        
        Args:
            issue_id: Jira issue ID
            status: New status (e.g., "In Progress", "Done")
            
        Returns:
            Transition result
        """
        # Use the async version via asyncio
        import asyncio
        return asyncio.run(self.transition_issue_async(issue_id, status))
    
    async def transition_issue_async(self, issue_id: str, status: str) -> Dict[str, Any]:
        """Async version of transition_issue.
        
        Args:
            issue_id: Jira issue ID
            status: New status
            
        Returns:
            Transition result
        """
        # First, get available transitions
        transitions_url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}/transitions"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            # Get available transitions
            async with session.get(transitions_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"Failed to get transitions: {response.status} - {error_text}"
                    }
                
                transitions_data = await response.json()
                transitions = transitions_data.get('transitions', [])
                
                # Find the transition ID for the desired status
                transition_id = None
                for transition in transitions:
                    to_status = transition.get('to', {}).get('name', '')
                    if to_status.lower() == status.lower():
                        transition_id = transition.get('id')
                        break
                
                if not transition_id:
                    available_statuses = [t.get('to', {}).get('name') for t in transitions]
                    return {
                        'success': False,
                        'error': f"Status '{status}' not available. Available: {available_statuses}"
                    }
                
                # Perform the transition
                transition_data = {
                    'transition': {
                        'id': transition_id
                    }
                }
                
                async with session.post(transitions_url, headers=headers, json=transition_data) as trans_response:
                    if trans_response.status == 204:  # Success, no content
                        return {
                            'success': True,
                            'issue_id': issue_id,
                            'status': status,
                            'transition_id': transition_id
                        }
                    else:
                        error_text = await trans_response.text()
                        return {
                            'success': False,
                            'error': f"Failed to transition: {trans_response.status} - {error_text}"
                        }
    
    def get_transitions(self, issue_id: str) -> Dict[str, Any]:
        """Get available transitions for an issue.
        
        Args:
            issue_id: Jira issue ID
            
        Returns:
            Available transitions data
        """
        # Use the async version via asyncio
        import asyncio
        return asyncio.run(self.get_transitions_async(issue_id))
    
    async def get_transitions_async(self, issue_id: str) -> Dict[str, Any]:
        """Async version of get_transitions.
        
        Args:
            issue_id: Jira issue ID
            
        Returns:
            Available transitions data
        """
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}/transitions"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get transitions: {response.status} - {error_text}")
    
    def transition_issue_by_id(self, issue_id: str, transition_id: str) -> Dict[str, Any]:
        """Transition issue using transition ID directly.
        
        Args:
            issue_id: Jira issue ID
            transition_id: Transition ID to execute
            
        Returns:
            Transition result
        """
        # Use the async version via asyncio
        import asyncio
        return asyncio.run(self.transition_issue_by_id_async(issue_id, transition_id))
    
    async def transition_issue_by_id_async(self, issue_id: str, transition_id: str) -> Dict[str, Any]:
        """Async version of transition_issue_by_id.
        
        Args:
            issue_id: Jira issue ID
            transition_id: Transition ID to execute
            
        Returns:
            Transition result
        """
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}/transitions"
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json'
        }
        
        transition_data = {
            'transition': {
                'id': transition_id
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=transition_data) as response:
                if response.status == 204:  # Success, no content
                    return {
                        'success': True,
                        'issue_id': issue_id,
                        'transition_id': transition_id
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"Failed to transition: {response.status} - {error_text}"
                    }