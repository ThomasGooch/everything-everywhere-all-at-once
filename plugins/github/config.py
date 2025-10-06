"""Configuration management for GitHub plugin."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubConfig:
    """Configuration for GitHub plugin loaded from environment variables."""

    token: str
    repo_owner: str
    repo_name: str
    base_branch: str = "main"

    @classmethod
    def from_env(cls) -> Optional["GitHubConfig"]:
        """Load configuration from environment variables.

        Expected environment variables:
        - GITHUB_TOKEN or GITHUB_API_TOKEN: GitHub personal access token
        - GITHUB_REPO_OWNER: Repository owner/organization
        - GITHUB_REPO_NAME: Repository name
        - GITHUB_BASE_BRANCH: Base branch (defaults to 'main')

        Returns:
            GitHubConfig instance if all required variables are present, None otherwise
        """
        # Load from environment variables (support multiple naming conventions)
        env_config = {
            "token": os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_TOKEN"),
            "repo_owner": os.getenv("GITHUB_REPO_OWNER") or os.getenv("GITHUB_OWNER"),
            "repo_name": os.getenv("GITHUB_REPO_NAME")
            or os.getenv("GITHUB_REPOSITORY"),
            "base_branch": os.getenv("GITHUB_BASE_BRANCH", "main"),  # Default to 'main'
        }

        # Check if all required variables are present (excluding base_branch which has default)
        required_vars = ["token", "repo_owner", "repo_name"]
        if not all(env_config[key] for key in required_vars):
            return None

        return cls(**env_config)

    @property
    def repo_full_name(self) -> str:
        """Get the full repository name in 'owner/repo' format."""
        return f"{self.repo_owner}/{self.repo_name}"

    @property
    def repo_url(self) -> str:
        """Get the HTTPS repository URL."""
        return f"https://github.com/{self.repo_full_name}.git"

    @property
    def repo_ssh_url(self) -> str:
        """Get the SSH repository URL."""
        return f"git@github.com:{self.repo_full_name}.git"
