"""GitHub plugin implementation for version control operations"""

import json
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

    # Enhanced GitHub Plugin Methods for Phase 4

    def _generate_branch_name(self, strategy: str, **kwargs) -> str:
        """Generate branch name using configured strategies"""

        branch_strategies = self.config.get("options", {}).get("branch_strategies", {})

        if strategy not in branch_strategies:
            # Fallback to default pattern
            if strategy == "feature":
                pattern = "feature/{task_id}-{title_slug}"
            elif strategy == "hotfix":
                pattern = "hotfix/{task_id}-{title_slug}"
            elif strategy == "release":
                pattern = "release/{version}"
            else:
                pattern = f"{strategy}/{task_id}"
        else:
            pattern = branch_strategies[strategy]

        # Replace template variables
        try:
            return pattern.format(**kwargs)
        except KeyError as e:
            logger.warning(
                f"Missing template variable {e} for branch strategy {strategy}"
            )
            # Fallback to simple pattern
            task_id = kwargs.get("task_id", "unknown")
            return f"{strategy}/{task_id}"

    def _get_auto_reviewers(self, file_changes: Dict[str, List[str]]) -> List[str]:
        """Get automatic reviewers based on configured rules"""

        reviewers = set()
        auto_reviewer_rules = (
            self.config.get("options", {}).get("auto_reviewers", {}).get("rules", [])
        )

        all_files = []
        for file_list in file_changes.values():
            all_files.extend(file_list)

        # Check path-based rules
        for rule in auto_reviewer_rules:
            if "path_pattern" in rule:
                pattern = rule["path_pattern"]
                for file_path in all_files:
                    if self._matches_pattern(file_path, pattern):
                        reviewers.update(rule.get("reviewers", []))

            # Check size-based rules
            elif "size_threshold" in rule:
                if len(all_files) >= rule["size_threshold"]:
                    reviewers.update(rule.get("reviewers", []))

        return list(reviewers)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a pattern"""

        # Convert glob pattern to regex
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)

    def _render_pr_template(
        self, template_type: str, template_data: Dict[str, Any]
    ) -> str:
        """Render PR template with provided data"""

        if template_type == "ai_generated":
            return self._render_ai_generated_pr_template(template_data)
        elif template_type == "default":
            return self._render_default_pr_template(template_data)
        else:
            return self._render_default_pr_template(template_data)

    def _render_ai_generated_pr_template(self, data: Dict[str, Any]) -> str:
        """Render AI-generated PR template"""

        task_data = data.get("task_data", {})
        impl_data = data.get("implementation_data", {})
        analysis_data = data.get("codebase_analysis", {})

        template = """## 🎯 Overview
{description}

## 🤖 AI Implementation Details

**Task**: {task_id} - {title}
**AI Cost**: ${ai_cost:.2f}
**Languages**: {languages}
**Frameworks**: {frameworks}

## 📁 Files Changed

### Modified Files:
{files_modified}

### New Files:
{files_created}

## 🧪 Testing

**Test Results**: {test_status}
**Test Framework**: {test_framework}

## ✅ Acceptance Criteria
{acceptance_criteria}

## 🔗 Related Links
- **Task**: [{task_id}]({task_url})

---

🤖 *This PR was generated by AI Development Agent*
*Please review carefully and provide feedback*"""

        files_modified = "\n".join(
            [f"- `{f}`" for f in impl_data.get("files_modified", [])]
        )
        files_created = "\n".join(
            [f"- `{f}`" for f in impl_data.get("files_created", [])]
        )

        test_results = impl_data.get("test_results", {})
        if test_results:
            test_status = f"✅ {test_results.get('passed', 0)}/{test_results.get('total', 0)} passed"
        else:
            test_status = "⏳ Tests will be run by CI/CD"

        return template.format(
            task_id=task_data.get("id", "N/A"),
            title=task_data.get("title", "No title"),
            description=task_data.get("description", "No description provided"),
            task_url=task_data.get("url", "#"),
            ai_cost=impl_data.get("ai_cost", 0.0),
            languages=", ".join(analysis_data.get("languages", ["Unknown"])),
            frameworks=", ".join(analysis_data.get("frameworks", ["Unknown"])),
            files_modified=files_modified or "- None",
            files_created=files_created or "- None",
            test_status=test_status,
            test_framework=analysis_data.get("test_framework", "Unknown"),
            acceptance_criteria=task_data.get(
                "acceptance_criteria", "- Implementation meets requirements"
            ),
        )

    def _render_default_pr_template(self, data: Dict[str, Any]) -> str:
        """Render default PR template"""

        task_data = data.get("task_data", {})
        impl_data = data.get("implementation_data", {})

        template = """## Description
{description}

## Changes
- {changes}

## Testing
{testing}

## Related Issues
- {task_id}"""

        changes = []
        if impl_data.get("files_modified"):
            changes.append(f"Modified {len(impl_data['files_modified'])} files")
        if impl_data.get("files_created"):
            changes.append(f"Created {len(impl_data['files_created'])} new files")

        return template.format(
            description=task_data.get("description", "No description provided"),
            changes=", ".join(changes) if changes else "See file changes",
            testing=impl_data.get("test_results", {}).get("summary", "Tests included"),
            task_id=task_data.get("id", "N/A"),
        )

    async def setup_workspace_with_analysis(
        self, workspace_config: Dict[str, Any]
    ) -> PluginResult:
        """Set up workspace with codebase analysis"""

        try:
            repository_url = workspace_config["repository_url"]
            strategy = workspace_config.get("branch_strategy", "feature")
            base_branch = workspace_config.get("base_branch", "main")

            # Generate branch name using strategy
            branch_name = self._generate_branch_name(
                strategy=strategy,
                task_id=workspace_config.get("task_id"),
                title_slug=workspace_config.get("title_slug"),
                version=workspace_config.get("version"),
            )

            # Clone repository
            workspace_path = (
                f"/tmp/workspace_{workspace_config.get('task_id', 'unknown')}"
            )
            clone_result = await self.clone_repository(repository_url, workspace_path)
            if not clone_result.success:
                return clone_result

            # Use actual path from clone result
            actual_workspace_path = clone_result.data.get("path", workspace_path)

            # Create feature branch
            branch_result = await self.create_branch(
                actual_workspace_path, branch_name, base_branch
            )
            if not branch_result.success:
                return branch_result

            result_data = {
                "workspace_path": actual_workspace_path,
                "branch_name": branch_name,
                "base_branch": base_branch,
            }

            # Perform codebase analysis if requested
            if workspace_config.get("analyze_codebase", False):
                analysis = self._analyze_codebase_structure(actual_workspace_path)
                result_data["codebase_analysis"] = analysis

            return PluginResult(
                success=True,
                data=result_data,
                metadata={"strategy_used": strategy, "repository": repository_url},
            )

        except Exception as e:
            logger.error(f"Error setting up workspace: {e}")
            return PluginResult(success=False, error=str(e))

    def _analyze_codebase_structure(self, workspace_path: str) -> Dict[str, Any]:
        """Analyze codebase structure and return metadata"""

        analysis = {
            "languages": [],
            "frameworks": [],
            "test_framework": None,
            "ci_config": None,
            "has_tests": False,
            "has_docs": False,
        }

        try:
            workspace = Path(workspace_path)

            # Detect languages by file extensions
            language_mapping = {
                ".py": "Python",
                ".js": "JavaScript",
                ".ts": "TypeScript",
                ".java": "Java",
                ".go": "Go",
                ".rs": "Rust",
                ".cpp": "C++",
                ".c": "C",
            }

            detected_languages = set()
            for file_path in workspace.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    if suffix in language_mapping:
                        detected_languages.add(language_mapping[suffix])

            analysis["languages"] = list(detected_languages)

            # Detect frameworks by config files
            framework_files = {
                "package.json": ["Node.js"],
                "requirements.txt": ["Python"],
                "pyproject.toml": ["Python"],
                "Cargo.toml": ["Rust"],
                "go.mod": ["Go"],
                "pom.xml": ["Java/Maven"],
            }

            detected_frameworks = set()
            for config_file, frameworks in framework_files.items():
                if (workspace / config_file).exists():
                    detected_frameworks.update(frameworks)

            # More specific framework detection
            if (workspace / "package.json").exists():
                try:
                    import json

                    with open(workspace / "package.json") as f:
                        package_data = json.load(f)
                        deps = {
                            **package_data.get("dependencies", {}),
                            **package_data.get("devDependencies", {}),
                        }

                        if "react" in deps:
                            detected_frameworks.add("React")
                        if "vue" in deps:
                            detected_frameworks.add("Vue.js")
                        if "express" in deps:
                            detected_frameworks.add("Express")
                except:
                    pass

            if (workspace / "requirements.txt").exists() or (
                workspace / "pyproject.toml"
            ).exists():
                # Check for common Python frameworks
                for file_path in workspace.rglob("*.py"):
                    content = file_path.read_text()
                    if "fastapi" in content.lower():
                        detected_frameworks.add("FastAPI")
                        break
                    elif "django" in content.lower():
                        detected_frameworks.add("Django")
                        break
                    elif "flask" in content.lower():
                        detected_frameworks.add("Flask")
                        break

            analysis["frameworks"] = list(detected_frameworks)

            # Detect test framework
            if any(workspace.rglob("*test*.py")):
                analysis["has_tests"] = True
                if (workspace / "pytest.ini").exists() or any(
                    "pytest" in f.name for f in workspace.rglob("*")
                ):
                    analysis["test_framework"] = "pytest"
                else:
                    analysis["test_framework"] = "unittest"
            elif any(workspace.rglob("*.test.js")):
                analysis["has_tests"] = True
                analysis["test_framework"] = "Jest"

            # Check for CI configuration
            ci_files = [
                ".github/workflows",
                ".gitlab-ci.yml",
                "Jenkinsfile",
                ".circleci/config.yml",
            ]

            for ci_file in ci_files:
                if (workspace / ci_file).exists():
                    analysis["ci_config"] = ci_file
                    break

            # Check for documentation
            doc_files = ["README.md", "docs/", "documentation/"]
            for doc_file in doc_files:
                if (workspace / doc_file).exists():
                    analysis["has_docs"] = True
                    break

        except Exception as e:
            logger.error(f"Error analyzing codebase: {e}")

        return analysis

    async def create_pr_with_metadata(self, pr_data: Dict[str, Any]) -> PluginResult:
        """Create PR with rich metadata and auto-assigned reviewers"""

        try:
            repository = pr_data["repository"]
            source_branch = pr_data["source_branch"]
            target_branch = pr_data["target_branch"]
            title = pr_data["title"]

            # Generate PR body using template
            template_type = pr_data.get("template_type", "default")
            pr_body = self._render_pr_template(template_type, pr_data)

            # Get auto-assigned reviewers
            file_changes = pr_data.get("implementation_data", {}).get(
                "file_changes", {}
            )
            if file_changes:
                auto_reviewers = self._get_auto_reviewers(file_changes)
            else:
                auto_reviewers = []

            # Combine with explicitly requested reviewers
            requested_reviewers = pr_data.get("reviewers", [])
            all_reviewers = list(set(auto_reviewers + requested_reviewers))

            # Create PR
            pr_creation_data = {
                "title": title,
                "body": pr_body,
                "head": source_branch,
                "base": target_branch,
                "draft": pr_data.get("draft", False),
            }

            if all_reviewers:
                pr_creation_data["reviewers"] = all_reviewers

            # Make API call
            url = f"https://api.github.com/repos/{repository}/pulls"

            async with self._session.post(
                url,
                headers=self._get_request_headers(),
                data=json.dumps(pr_creation_data),
            ) as response:
                if response.status == 201:
                    pr_response = await response.json()

                    # Add labels if specified
                    labels = pr_data.get("labels", [])
                    if labels:
                        await self.update_pr_labels_and_milestone(
                            repository, pr_response["number"], labels
                        )

                    return PluginResult(
                        success=True,
                        data={
                            "pr_id": pr_response["id"],
                            "pr_number": pr_response["number"],
                            "pr_url": pr_response["html_url"],
                            "reviewers_assigned": all_reviewers,
                            "auto_reviewers": auto_reviewers,
                        },
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to create PR: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error creating PR with metadata: {e}")
            return PluginResult(success=False, error=str(e))

    async def trigger_github_actions(
        self,
        repository: str,
        workflow_name: str,
        branch: str,
        inputs: Dict[str, Any] = None,
    ) -> PluginResult:
        """Trigger GitHub Actions workflow"""

        try:
            url = f"https://api.github.com/repos/{repository}/actions/workflows/{workflow_name}/dispatches"

            data = {"ref": branch, "inputs": inputs or {}}

            async with self._session.post(
                url, headers=self._get_request_headers(), data=json.dumps(data)
            ) as response:
                if response.status == 204:
                    return PluginResult(
                        success=True,
                        data={
                            "workflow_triggered": True,
                            "workflow": workflow_name,
                            "branch": branch,
                        },
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to trigger workflow: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error triggering GitHub Actions: {e}")
            return PluginResult(success=False, error=str(e))

    async def analyze_repository_structure(
        self, repository: str, branch: str = "main"
    ) -> PluginResult:
        """Analyze remote repository structure"""

        try:
            url = f"https://api.github.com/repos/{repository}/git/trees/{branch}?recursive=1"

            async with self._session.get(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == 200:
                    tree_data = await response.json()

                    analysis = {
                        "languages": set(),
                        "has_ci": False,
                        "has_tests": False,
                        "has_docs": False,
                        "file_count": 0,
                    }

                    language_extensions = {
                        ".py": "Python",
                        ".js": "JavaScript",
                        ".ts": "TypeScript",
                        ".java": "Java",
                        ".go": "Go",
                        ".rs": "Rust",
                    }

                    for item in tree_data.get("tree", []):
                        if item["type"] == "blob":
                            path = item["path"]
                            analysis["file_count"] += 1

                            # Detect languages
                            for ext, lang in language_extensions.items():
                                if path.endswith(ext):
                                    analysis["languages"].add(lang)

                            # Detect JavaScript from package files
                            if path in [
                                "package.json",
                                "package-lock.json",
                                "yarn.lock",
                            ]:
                                analysis["languages"].add("JavaScript")

                            # Detect CI/CD
                            if ".github/workflows" in path or path.endswith(".yml"):
                                analysis["has_ci"] = True

                            # Detect tests
                            if "test" in path.lower() or path.startswith("tests/"):
                                analysis["has_tests"] = True

                            # Detect docs
                            if path.lower() in [
                                "readme.md",
                                "readme.txt",
                            ] or path.startswith("docs/"):
                                analysis["has_docs"] = True

                    analysis["languages"] = list(analysis["languages"])

                    return PluginResult(success=True, data={"analysis": analysis})
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to analyze repository: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            return PluginResult(success=False, error=str(e))

    async def get_pr_status(self, repository: str, pr_number: int) -> PluginResult:
        """Get PR status with checks and reviews"""

        try:
            url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}"

            async with self._session.get(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == 200:
                    pr_data = await response.json()

                    # Get status checks
                    checks_url = f"https://api.github.com/repos/{repository}/commits/{pr_data['head']['sha']}/status"
                    async with self._session.get(
                        checks_url, headers=self._get_request_headers()
                    ) as checks_response:
                        if checks_response.status == 200:
                            checks_data = await checks_response.json()
                            status_checks = {
                                status["context"]: status["state"]
                                for status in checks_data.get("statuses", [])
                            }
                        else:
                            status_checks = {}

                    # Get reviews
                    reviews_url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}/reviews"
                    async with self._session.get(
                        reviews_url, headers=self._get_request_headers()
                    ) as reviews_response:
                        if reviews_response.status == 200:
                            reviews_data = await reviews_response.json()
                            review_summary = {
                                "approved": 0,
                                "changes_requested": 0,
                                "commented": 0,
                            }

                            for review in reviews_data:
                                state = review["state"].lower()
                                if state == "approved":
                                    review_summary["approved"] += 1
                                elif state == "changes_requested":
                                    review_summary["changes_requested"] += 1
                                elif state == "commented":
                                    review_summary["commented"] += 1
                        else:
                            review_summary = {}

                    status = {
                        "state": pr_data["state"],
                        "mergeable": pr_data["mergeable"],
                        "checks": status_checks,
                        "reviews": review_summary,
                    }

                    return PluginResult(success=True, data={"status": status})
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to get PR status: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error getting PR status: {e}")
            return PluginResult(success=False, error=str(e))

    async def merge_pr_with_strategy(
        self,
        repository: str,
        pr_number: int,
        merge_method: str = "merge",
        commit_title: str = None,
        commit_message: str = None,
    ) -> PluginResult:
        """Merge PR with specified strategy"""

        try:
            url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}/merge"

            data = {"merge_method": merge_method}
            if commit_title:
                data["commit_title"] = commit_title
            if commit_message:
                data["commit_message"] = commit_message

            async with self._session.put(
                url, headers=self._get_request_headers(), data=json.dumps(data)
            ) as response:
                if response.status == 200:
                    merge_data = await response.json()
                    return PluginResult(
                        success=True,
                        data={
                            "merged": merge_data["merged"],
                            "commit_sha": merge_data["sha"],
                            "message": merge_data["message"],
                        },
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to merge PR: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error merging PR: {e}")
            return PluginResult(success=False, error=str(e))

    async def update_pr_labels_and_milestone(
        self,
        repository: str,
        pr_number: int,
        labels: List[str] = None,
        milestone: str = None,
    ) -> PluginResult:
        """Update PR labels and milestone"""

        try:
            url = f"https://api.github.com/repos/{repository}/issues/{pr_number}"

            data = {}
            if labels:
                data["labels"] = labels
            if milestone:
                # First get milestone ID
                milestones_url = f"https://api.github.com/repos/{repository}/milestones"
                async with self._session.get(
                    milestones_url, headers=self._get_request_headers()
                ) as ms_response:
                    if ms_response.status == 200:
                        milestones = await ms_response.json()
                        milestone_id = next(
                            (
                                m["number"]
                                for m in milestones
                                if m["title"] == milestone
                            ),
                            None,
                        )
                        if milestone_id:
                            data["milestone"] = milestone_id

            if not data:
                return PluginResult(success=True, data={"message": "No updates needed"})

            async with self._session.patch(
                url, headers=self._get_request_headers(), data=json.dumps(data)
            ) as response:
                if response.status == 200:
                    updated_data = await response.json()
                    return PluginResult(
                        success=True,
                        data={
                            "labels": [
                                label["name"]
                                for label in updated_data.get("labels", [])
                            ],
                            "milestone": updated_data.get("milestone", {}).get("title")
                            if updated_data.get("milestone")
                            else None,
                        },
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to update labels/milestone: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error updating PR labels/milestone: {e}")
            return PluginResult(success=False, error=str(e))

    async def create_draft_pr(
        self,
        repository: str,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
    ) -> PluginResult:
        """Create draft PR"""

        try:
            pr_data = {
                "title": title,
                "body": body,
                "head": source_branch,
                "base": target_branch,
                "draft": True,
            }

            url = f"https://api.github.com/repos/{repository}/pulls"

            async with self._session.post(
                url, headers=self._get_request_headers(), data=json.dumps(pr_data)
            ) as response:
                if response.status == 201:
                    pr_response = await response.json()
                    return PluginResult(
                        success=True,
                        data={
                            "pr_id": pr_response["id"],
                            "pr_number": pr_response["number"],
                            "pr_url": pr_response["html_url"],
                            "is_draft": pr_response["draft"],
                        },
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to create draft PR: {response.status} - {error_text}",
                    )

        except Exception as e:
            logger.error(f"Error creating draft PR: {e}")
            return PluginResult(success=False, error=str(e))
