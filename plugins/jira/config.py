"""Configuration management for Jira plugin."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class JiraConfig:
    """Configuration for Jira plugin loaded from environment variables."""

    base_url: str
    api_key: str
    username: str
    project_key: str

    @classmethod
    def from_env(cls) -> Optional["JiraConfig"]:
        """Load configuration from environment variables.

        Returns:
            JiraConfig instance if all required variables are present, None otherwise
        """
        # First try environment variables (support multiple naming conventions)
        env_config = {
            "base_url": os.getenv("JIRA_BASE_URL") or os.getenv("JIRA_URL"),
            "api_key": os.getenv("JIRA_API_KEY") or os.getenv("JIRA_API_TOKEN"),
            "username": os.getenv("JIRA_USERNAME") or os.getenv("JIRA_EMAIL"),
            "project_key": os.getenv("JIRA_PROJECT_KEY", "DEMO"),  # Default project key
        }

        # Note: Enhanced key management was removed during cleanup
        # All configuration now comes from environment variables only

        # Check if all required variables are present
        if not all(env_config.values()):
            return None

        return cls(**env_config)
