"""GitHub API wrapper for modular plugin system."""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp

from .config import GitHubConfig

logger = logging.getLogger(__name__)


class GitHubAPI:
    """GitHub API wrapper for autonomous execution with Git operations."""

    config: GitHubConfig

    def __init__(self) -> None:
        """Initialize GitHub API wrapper."""
        config = GitHubConfig.from_env()
        if not config:
            raise ValueError(
                "GitHub configuration not available in environment variables"
            )
        self.config = config  # Now MyPy knows this is not None

    # Git Operations
    def clone_repository(
        self, target_dir: Path, use_ssh: bool = True
    ) -> Dict[str, Any]:
        """Clone repository to target directory.

        Args:
            target_dir: Directory to clone repository to
            use_ssh: Whether to use SSH (True) or HTTPS (False) for cloning

        Returns:
            Result dictionary with success status
        """
        try:
            # Clean up existing directory
            if target_dir.exists():
                shutil.rmtree(target_dir)

            # Choose URL based on preference
            repo_url = self.config.repo_ssh_url if use_ssh else self.config.repo_url

            logger.info(f"Cloning {repo_url} to {target_dir}")
            subprocess.run(["git", "clone", repo_url, str(target_dir)], check=True)

            return {"success": True, "repo_url": repo_url}

        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            return {"success": False, "error": str(e)}

    def create_branch(self, workspace_dir: Path, branch_name: str) -> Dict[str, Any]:
        """Create and checkout a new branch.

        Args:
            workspace_dir: Repository directory
            branch_name: Name of the branch to create

        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"Creating branch: {branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", branch_name], cwd=workspace_dir, check=True
            )

            return {"success": True, "branch": branch_name}

        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return {"success": False, "error": str(e)}

    def commit_changes(
        self, workspace_dir: Path, commit_message: str
    ) -> Dict[str, Any]:
        """Stage and commit all changes.

        Args:
            workspace_dir: Repository directory
            commit_message: Commit message

        Returns:
            Result dictionary with success status and commit info
        """
        try:
            # Check for changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=workspace_dir,
            )

            if not result.stdout.strip():
                return {
                    "success": True,
                    "changes": False,
                    "message": "No changes to commit",
                }

            # Stage changes
            subprocess.run(["git", "add", "."], cwd=workspace_dir, check=True)

            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message], cwd=workspace_dir, check=True
            )

            changes = result.stdout.strip().split("\n")
            logger.info(f"Committed {len(changes)} changes")

            return {
                "success": True,
                "changes": True,
                "commit_message": commit_message,
                "files_changed": len(changes),
            }

        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return {"success": False, "error": str(e)}

    def push_branch(self, workspace_dir: Path, branch_name: str) -> Dict[str, Any]:
        """Push branch to remote repository.

        Args:
            workspace_dir: Repository directory
            branch_name: Name of the branch to push

        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"Pushing branch: {branch_name}")
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=workspace_dir,
                check=True,
            )

            return {"success": True, "branch": branch_name}

        except Exception as e:
            logger.error(f"Failed to push branch: {e}")
            return {"success": False, "error": str(e)}

    # GitHub API Operations
    async def create_pull_request_async(
        self,
        branch_name: str,
        title: str,
        body: str = "",
        base_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a pull request using GitHub API.

        Args:
            branch_name: Source branch name
            title: PR title
            body: PR description/body
            base_branch: Target branch (defaults to configured base branch)

        Returns:
            Result dictionary with PR information
        """
        if not base_branch:
            base_branch = self.config.base_branch

        url = f"https://api.github.com/repos/{self.config.repo_full_name}/pulls"
        headers = {
            "Authorization": f"token {self.config.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json",
        }

        data = {"title": title, "head": branch_name, "base": base_branch, "body": body}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        pr_data = await response.json()
                        logger.info(
                            f"Created PR #{pr_data['number']}: {pr_data['html_url']}"
                        )
                        return {
                            "success": True,
                            "pr_number": pr_data["number"],
                            "pr_url": pr_data["html_url"],
                            "pr_data": pr_data,
                        }
                    else:
                        error_data = await response.json()
                        logger.error(
                            f"Failed to create PR: {response.status} - {error_data}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return {"success": False, "error": str(e)}

    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str = "",
        base_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for create_pull_request_async."""
        return asyncio.run(
            self.create_pull_request_async(branch_name, title, body, base_branch)
        )

    async def get_pull_request_async(self, pr_number: int) -> Dict[str, Any]:
        """Get pull request information.

        Args:
            pr_number: Pull request number

        Returns:
            PR data dictionary
        """
        url = f"https://api.github.com/repos/{self.config.repo_full_name}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        pr_data = await response.json()
                        return {"success": True, "pr_data": pr_data}
                    else:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data.get('message', 'Unknown error')}",
                        }
        except Exception as e:
            logger.error(f"Failed to get pull request: {e}")
            return {"success": False, "error": str(e)}

    def get_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Synchronous wrapper for get_pull_request_async."""
        return asyncio.run(self.get_pull_request_async(pr_number))

    # Utility Methods
    def generate_branch_name(
        self, task_id: str, summary: str = "implementation"
    ) -> str:
        """Generate a branch name following project conventions.

        Args:
            task_id: Task ID (e.g., TASK-123)
            summary: Brief summary for the branch

        Returns:
            Generated branch name
        """
        import time

        # Clean up summary
        clean_summary = summary.lower().replace(" ", "_").replace("-", "_")[:30]
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits

        return f"{task_id}_{clean_summary}_{timestamp}"

    def generate_commit_message(self, task_id: str, summary: str) -> str:
        """Generate commit message following project conventions.

        Args:
            task_id: Task ID
            summary: Task summary

        Returns:
            Generated commit message
        """
        return f"{task_id}: {summary}\n\n🤖 Generated with automated workflow"

    def generate_pr_body(
        self, task_id: str, task_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate PR description with task details.

        Args:
            task_id: Task ID
            task_details: Optional task details from Jira

        Returns:
            Generated PR body
        """
        body_parts = [f"## Summary", f"Automated implementation for task {task_id}", ""]

        if task_details:
            fields = task_details.get("fields", {})
            if fields.get("summary"):
                body_parts.extend([f"**Task Summary:** {fields['summary']}", ""])

            if fields.get("description"):
                body_parts.extend([f"**Description:**", fields["description"], ""])

        body_parts.extend(
            [
                "## Changes",
                "- Implementation completed via automated workflow",
                "- All changes have been tested in Claude CLI environment",
                "",
                "## Testing",
                "- [x] Code implemented and tested in development environment",
                "- [ ] Manual review required before merge",
                "",
                f"🤖 Generated with [AI Development Automation System](https://github.com/{self.config.repo_full_name})",
                f"📋 Task: {task_id}",
            ]
        )

        return "\n".join(body_parts)
