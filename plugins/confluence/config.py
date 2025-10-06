"""Configuration management for Confluence plugin."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfluenceConfig:
    """Configuration for Confluence plugin loaded from environment variables."""

    base_url: str
    username: str
    api_key: str
    space_key: str

    @classmethod
    def from_env(cls) -> Optional["ConfluenceConfig"]:
        """Load configuration from environment variables.

        Expected environment variables:
        - CONFLUENCE_BASE_URL: Confluence instance URL (e.g., https://company.atlassian.net)
        - CONFLUENCE_USERNAME: Username/email for authentication
        - CONFLUENCE_API_KEY or CONFLUENCE_API_TOKEN: API token
        - CONFLUENCE_SPACE_KEY: Default space key for documentation

        Falls back to Jira config if Confluence-specific vars not found.

        Returns:
            ConfluenceConfig instance if all required variables are present, None otherwise
        """
        # Try Confluence-specific environment variables first
        base_url = os.getenv("CONFLUENCE_BASE_URL")
        username = os.getenv("CONFLUENCE_USERNAME")
        api_key = os.getenv("CONFLUENCE_API_KEY") or os.getenv("CONFLUENCE_API_TOKEN")
        space_key = os.getenv("CONFLUENCE_SPACE_KEY")

        # Fall back to Jira config (since Atlassian uses same credentials)
        if not base_url:
            base_url = os.getenv("JIRA_BASE_URL")
        if not username:
            username = os.getenv("JIRA_USERNAME")
        if not api_key:
            api_key = os.getenv("JIRA_API_KEY") or os.getenv("JIRA_API_TOKEN")
        if not space_key:
            # Default space key based on project
            project_key = os.getenv("JIRA_PROJECT_KEY", "DEV")
            space_key = f"{project_key}DOC"

        # Check if all required variables are present
        if not all([base_url, username, api_key, space_key]):
            return None

        return cls(
            base_url=base_url,
            username=username,
            api_key=api_key,
            space_key=space_key,
        )
