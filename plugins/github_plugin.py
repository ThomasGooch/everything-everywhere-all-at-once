"""GitHub plugin implementation for version control operations"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import git
from aiohttp import ClientSession

from core.plugin_interface import (
    PluginConnectionError,
    PluginResult,
    PluginStatus,
    PluginType,
    PluginValidationError,
    VersionControlPlugin,
)

logger = logging.getLogger(__name__)

# Constants for GitHub API
GITHUB_API_VERSION = "2022-11-28"  # GitHub API version header
DEFAULT_TIMEOUT = 60
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_BRANCH = "main"

# GitHub-specific constants
GITHUB_TOKEN_PREFIXES = ("ghp_", "github_pat_")
GITHUB_REMOTE_NAME = "origin"

# HTTP Status codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_UNPROCESSABLE_ENTITY = 422

# Git branch validation patterns
INVALID_BRANCH_PATTERNS = [
    r"^\.",  # Can't start with dot
    r"\.$",  # Can't end with dot
    r"\.\.",  # Can't contain double dots
    r"[\s~^:?*\[\]\\]",  # Can't contain these special characters
    r"@{",  # Can't contain @{
]


class GitHubPlugin(VersionControlPlugin):
    """GitHub integration plugin for version control operations"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize GitHub plugin

        Args:
            config: Plugin configuration dictionary
        """
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._api_url = ""
        self._token = ""

    def get_plugin_type(self) -> PluginType:
        """Return plugin type"""
        return PluginType.VERSION_CONTROL

    def get_plugin_name(self) -> str:
        """Return plugin name"""
        return "github"

    def get_version(self) -> str:
        """Return plugin version"""
        return "1.0.0"

    def get_required_config_keys(self) -> List[str]:
        """Return required configuration keys"""
        return ["connection.token", "connection.api_url"]

    def get_optional_config_keys(self) -> List[str]:
        """Return optional configuration keys"""
        return [
            "options.timeout",
            "options.retry_attempts",
            "options.default_branch",
            "options.auto_create_branches",
            "options.require_pr_reviews",
            "options.merge_strategy",
            "mappings",
        ]

    def validate_config(self) -> bool:
        """Validate plugin configuration

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid
        """
        connection = self.config.get("connection", {})

        # Check required fields
        if not connection.get("token"):
            raise PluginValidationError(
                "Missing required configuration: connection.token"
            )

        if not connection.get("api_url"):
            raise PluginValidationError(
                "Missing required configuration: connection.api_url"
            )

        # Validate token format (GitHub personal access tokens)
        token = connection["token"]
        if not any(token.startswith(prefix) for prefix in GITHUB_TOKEN_PREFIXES):
            raise PluginValidationError(
                f"GitHub token should start with one of: {', '.join(GITHUB_TOKEN_PREFIXES)}"
            )

        # Validate API URL
        api_url = connection["api_url"]
        if not api_url.startswith("https://"):
            raise PluginValidationError("GitHub API URL must use HTTPS")

        return True

    async def initialize(self) -> bool:
        """Initialize plugin and establish connection

        Returns:
            True if initialization successful
        """
        try:
            # Validate configuration first
            self.validate_config()

            # Extract connection details
            connection = self.config["connection"]
            self._api_url = connection["api_url"].rstrip("/")
            self._token = connection["token"]

            # Create HTTP session
            timeout = aiohttp.ClientTimeout(
                total=self.config.get("options", {}).get("timeout", DEFAULT_TIMEOUT)
            )
            self._session = ClientSession(timeout=timeout)

            # Test connection
            await self._test_connection()

            self._is_initialized = True
            self._connection_established = True

            logger.info(f"Successfully initialized GitHub plugin for {self._api_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize GitHub plugin: {e}")
            self._is_initialized = False
            self._connection_established = False

            # Cleanup session if created
            if self._session:
                await self._session.close()
                self._session = None

            return False

    async def cleanup(self) -> bool:
        """Clean up plugin resources

        Returns:
            True if cleanup successful
        """
        try:
            if self._session:
                await self._session.close()
                self._session = None

            self._is_initialized = False
            self._connection_established = False

            logger.info("GitHub plugin cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during GitHub plugin cleanup: {e}")
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
            # Simple health check - get authenticated user
            async with self._session.get(
                self._get_api_url("user"), headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    return PluginStatus.HEALTHY
                else:
                    logger.warning(
                        f"GitHub health check returned status {response.status}"
                    )
                    return PluginStatus.DEGRADED

        except Exception as e:
            logger.error(f"GitHub health check failed: {e}")
            return PluginStatus.UNHEALTHY

    async def clone_repository(self, url: str, local_path: str) -> PluginResult:
        """Clone repository to local path

        Args:
            url: Repository URL (can be HTTPS or SSH)
            local_path: Local directory path

        Returns:
            PluginResult indicating success/failure
        """
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Clone repository using GitPython
            repo = git.Repo.clone_from(url, local_path)

            logger.info(f"Successfully cloned repository {url} to {local_path}")

            return PluginResult(
                success=True,
                data={
                    "repository_url": url,
                    "local_path": local_path,
                    "active_branch": repo.active_branch.name,
                    "commit_count": len(list(repo.iter_commits())),
                },
                metadata={"git_dir": repo.git_dir},
            )

        except Exception as e:
            logger.error(f"Error cloning repository {url}: {e}")
            return PluginResult(success=False, error=f"Failed to clone repository: {e}")

    async def create_branch(
        self, repo_path: str, branch_name: str, base_branch: str = "main"
    ) -> PluginResult:
        """Create a new branch

        Args:
            repo_path: Local repository path
            branch_name: Name for new branch
            base_branch: Base branch to create from

        Returns:
            PluginResult indicating success/failure
        """
        try:
            # Validate branch name
            if not self._validate_branch_name(branch_name):
                return PluginResult(
                    success=False, error=f"Invalid branch name: {branch_name}"
                )

            repo = git.Repo(repo_path)

            # Ensure we're on the base branch
            if base_branch in repo.heads:
                base_head = repo.heads[base_branch]
            else:
                # Try to find the base branch in remote
                remote_branch = f"origin/{base_branch}"
                if remote_branch in [ref.name for ref in repo.refs]:
                    base_head = repo.refs[remote_branch]
                else:
                    return PluginResult(
                        success=False, error=f"Base branch '{base_branch}' not found"
                    )

            # Create new branch
            new_branch = repo.create_head(branch_name, base_head)
            new_branch.checkout()

            logger.info(
                f"Created and checked out branch '{branch_name}' from '{base_branch}'"
            )

            return PluginResult(
                success=True,
                data={
                    "branch_name": branch_name,
                    "base_branch": base_branch,
                    "commit_hash": str(new_branch.commit),
                },
            )

        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {e}")
            return PluginResult(success=False, error=f"Failed to create branch: {e}")

    async def commit_changes(
        self, repo_path: str, message: str, files: List[str]
    ) -> PluginResult:
        """Commit changes to repository

        Args:
            repo_path: Local repository path
            message: Commit message
            files: List of files to commit (empty list = all changes)

        Returns:
            PluginResult with commit hash
        """
        try:
            repo = git.Repo(repo_path)

            # Stage files
            if files:
                # Stage specific files
                repo.index.add(files)
            else:
                # Stage all changes
                repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.index.diff("HEAD"):
                return PluginResult(success=False, error="No changes to commit")

            # Create commit
            commit = repo.index.commit(message)

            logger.info(f"Created commit {commit.hexsha[:8]} with message: {message}")

            return PluginResult(
                success=True,
                data={
                    "commit_hash": commit.hexsha,
                    "message": message,
                    "files": files if files else "all_changes",
                    "author": str(commit.author),
                    "timestamp": commit.committed_datetime.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return PluginResult(success=False, error=f"Failed to commit changes: {e}")

    async def push_branch(self, repo_path: str, branch_name: str) -> PluginResult:
        """Push branch to remote

        Args:
            repo_path: Local repository path
            branch_name: Branch to push

        Returns:
            PluginResult indicating success/failure
        """
        try:
            repo = git.Repo(repo_path)

            # Get remote (usually 'origin')
            if GITHUB_REMOTE_NAME not in repo.remotes:
                return PluginResult(
                    success=False, error=f"No '{GITHUB_REMOTE_NAME}' remote found"
                )

            origin = repo.remotes[GITHUB_REMOTE_NAME]

            # Push branch
            push_info = origin.push(branch_name)

            if push_info and push_info[0].flags & git.PushInfo.ERROR:
                return PluginResult(
                    success=False, error=f"Push failed: {push_info[0].summary}"
                )

            logger.info(f"Successfully pushed branch '{branch_name}' to remote")

            return PluginResult(
                success=True,
                data={
                    "branch_name": branch_name,
                    "remote": "origin",
                    "push_summary": push_info[0].summary if push_info else "success",
                },
            )

        except Exception as e:
            logger.error(f"Error pushing branch {branch_name}: {e}")
            return PluginResult(success=False, error=f"Failed to push branch: {e}")

    async def create_pull_request(
        self, repo_path: str, pr_data: Dict[str, Any]
    ) -> PluginResult:
        """Create pull request

        Args:
            repo_path: Local repository path (used to determine repository)
            pr_data: Pull request information containing:
                - title: PR title
                - body: PR description
                - head: Source branch
                - base: Target branch
                - repository: Repository in format "owner/repo"

        Returns:
            PluginResult with PR URL
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            repository = pr_data.get("repository")
            if not repository:
                return PluginResult(
                    success=False, error="Repository not specified in pr_data"
                )

            # Build PR payload
            payload = {
                "title": pr_data.get("title", ""),
                "body": pr_data.get("body", ""),
                "head": pr_data.get("head", ""),
                "base": pr_data.get("base", "main"),
                "draft": pr_data.get("draft", False),
            }

            url = self._get_api_url(f"repos/{repository}/pulls")

            async with self._session.post(
                url, headers=self._get_request_headers(), json=payload
            ) as response:
                if response.status == HTTP_UNPROCESSABLE_ENTITY:
                    error_data = await response.json()
                    return PluginResult(
                        success=False,
                        error=f"PR validation failed: {error_data.get('message', 'Unknown error')}",
                    )
                elif response.status != HTTP_CREATED:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to create PR: {response.status} {error_text}",
                    )

                pr_response = await response.json()

                logger.info(
                    f"Created PR #{pr_response['number']}: {pr_response['html_url']}"
                )

                return PluginResult(
                    success=True,
                    data={
                        "pr_url": pr_response["html_url"],
                        "pr_number": pr_response["number"],
                        "pr_id": pr_response["id"],
                        "title": pr_response["title"],
                        "state": pr_response["state"],
                    },
                    metadata={"raw_response": pr_response},
                )

        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return PluginResult(
                success=False, error=f"Failed to create pull request: {e}"
            )

    async def get_repository_info(self, repository: str) -> PluginResult:
        """Get repository information

        Args:
            repository: Repository in format "owner/repo"

        Returns:
            PluginResult with repository metadata
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            url = self._get_api_url(f"repos/{repository}")

            async with self._session.get(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_NOT_FOUND:
                    return PluginResult(
                        success=False, error=f"Repository {repository} not found"
                    )
                elif response.status != HTTP_OK:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"API error {response.status}: {error_text}",
                    )

                repo_data = await response.json()

                return PluginResult(
                    success=True,
                    data={
                        "full_name": repo_data["full_name"],
                        "name": repo_data["name"],
                        "owner": repo_data["owner"]["login"],
                        "default_branch": repo_data["default_branch"],
                        "clone_url": repo_data["clone_url"],
                        "ssh_url": repo_data["ssh_url"],
                        "private": repo_data["private"],
                        "description": repo_data.get("description", ""),
                        "language": repo_data.get("language", ""),
                    },
                    metadata={"raw_response": repo_data},
                )

        except Exception as e:
            logger.error(f"Error getting repository info for {repository}: {e}")
            return PluginResult(
                success=False, error=f"Failed to get repository info: {e}"
            )

    async def _test_connection(self) -> None:
        """Test connection to GitHub API

        Raises:
            PluginConnectionError: If connection test fails
        """
        try:
            url = self._get_api_url("user")

            async with self._session.get(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_UNAUTHORIZED:
                    raise PluginConnectionError(
                        "Authentication failed - check GitHub token"
                    )
                elif response.status == HTTP_FORBIDDEN:
                    raise PluginConnectionError(
                        "Access forbidden - check token permissions"
                    )
                elif response.status != HTTP_OK:
                    error_text = await response.text()
                    raise PluginConnectionError(
                        f"Connection test failed: {response.status} {error_text}"
                    )

                user_info = await response.json()
                logger.info(
                    f"Connected to GitHub as user {user_info.get('login', 'unknown')}"
                )

        except aiohttp.ClientError as e:
            raise PluginConnectionError(f"Network error: {e}") from e

    def _get_api_url(self, endpoint: str) -> str:
        """Get full API URL for an endpoint

        Args:
            endpoint: API endpoint path (e.g., "repos/owner/repo")

        Returns:
            Full API URL
        """
        return f"{self._api_url}/{endpoint.lstrip('/')}"

    def _get_request_headers(
        self, content_type: str = "application/json"
    ) -> Dict[str, str]:
        """Get standard request headers

        Args:
            content_type: Content type header value

        Returns:
            Dictionary of headers
        """
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _parse_repository_identifier(self, repo_input: str) -> Tuple[str, str]:
        """Parse repository identifier from various formats

        Args:
            repo_input: Repository in various formats

        Returns:
            Tuple of (owner, repo_name)
        """
        # Remove common prefixes and suffixes
        repo_input = repo_input.strip()

        # Handle different URL formats
        if repo_input.startswith("https://github.com/"):
            repo_input = repo_input.replace("https://github.com/", "")
        elif repo_input.startswith("git@github.com:"):
            repo_input = repo_input.replace("git@github.com:", "")

        # Remove .git suffix
        if repo_input.endswith(".git"):
            repo_input = repo_input[:-4]

        # Split owner/repo
        parts = repo_input.split("/")
        if len(parts) != 2:
            raise PluginValidationError(f"Invalid repository format: {repo_input}")

        return parts[0], parts[1]

    def _handle_api_response_error(
        self, response_status: int, error_text: str, operation: str
    ) -> PluginResult:
        """Handle common API response errors

        Args:
            response_status: HTTP response status code
            error_text: Error message from response
            operation: Description of the operation that failed

        Returns:
            PluginResult with appropriate error message
        """
        if response_status == HTTP_NOT_FOUND:
            return PluginResult(success=False, error=f"{operation}: Resource not found")
        elif response_status == HTTP_UNAUTHORIZED:
            return PluginResult(
                success=False, error=f"{operation}: Authentication failed"
            )
        elif response_status == HTTP_FORBIDDEN:
            return PluginResult(success=False, error=f"{operation}: Access forbidden")
        elif response_status == HTTP_UNPROCESSABLE_ENTITY:
            return PluginResult(
                success=False, error=f"{operation}: Validation failed - {error_text}"
            )
        else:
            return PluginResult(
                success=False,
                error=f"{operation}: API error {response_status} - {error_text}",
            )

    def _validate_branch_name(self, branch_name: str) -> bool:
        """Validate Git branch name according to Git rules

        Args:
            branch_name: Branch name to validate

        Returns:
            True if valid branch name
        """
        if not branch_name or not branch_name.strip():
            return False

        # Check against invalid patterns
        for pattern in INVALID_BRANCH_PATTERNS:
            if re.search(pattern, branch_name):
                return False

        return True
