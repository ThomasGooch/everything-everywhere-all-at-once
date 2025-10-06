"""GitHub utility functions and tools."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .api import GitHubAPI

logger = logging.getLogger(__name__)


class GitHubTools:
    """High-level GitHub workflow tools."""

    def __init__(self):
        """Initialize GitHub tools."""
        self.api = GitHubAPI()

    def setup_repository_workspace(
        self, target_dir: Path, task_id: str, task_summary: str = "implementation"
    ) -> Dict[str, Any]:
        """Set up complete repository workspace for a task.

        Args:
            target_dir: Directory to set up workspace in
            task_id: Task identifier
            task_summary: Brief task summary for branch naming

        Returns:
            Result dictionary with workspace info
        """
        try:
            # Clone repository
            clone_result = self.api.clone_repository(target_dir)
            if not clone_result["success"]:
                return {
                    "success": False,
                    "error": f"Clone failed: {clone_result['error']}",
                }

            # Generate branch name
            branch_name = self.api.generate_branch_name(task_id, task_summary)

            # Create branch
            branch_result = self.api.create_branch(target_dir, branch_name)
            if not branch_result["success"]:
                return {
                    "success": False,
                    "error": f"Branch creation failed: {branch_result['error']}",
                }

            logger.info(f"Workspace ready: {target_dir} on branch {branch_name}")

            return {
                "success": True,
                "workspace_dir": target_dir,
                "branch_name": branch_name,
                "repo_url": clone_result["repo_url"],
            }

        except Exception as e:
            logger.error(f"Failed to setup workspace: {e}")
            return {"success": False, "error": str(e)}

    async def complete_workflow_async(
        self,
        workspace_dir: Path,
        branch_name: str,
        task_id: str,
        task_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Complete the GitHub workflow: commit, push, create PR.

        Args:
            workspace_dir: Repository workspace directory
            branch_name: Branch name to push
            task_id: Task identifier
            task_details: Optional task details for PR description

        Returns:
            Result dictionary with PR information
        """
        try:
            # Generate commit message
            summary = "Implementation"
            if task_details and task_details.get("fields", {}).get("summary"):
                summary = task_details["fields"]["summary"]

            commit_message = self.api.generate_commit_message(task_id, summary)

            # Commit changes
            commit_result = self.api.commit_changes(workspace_dir, commit_message)
            if not commit_result["success"]:
                return {
                    "success": False,
                    "error": f"Commit failed: {commit_result['error']}",
                }

            # If no changes, still return success
            if not commit_result.get("changes", True):
                return {
                    "success": True,
                    "changes": False,
                    "message": "No changes to commit - workflow completed without modifications",
                }

            # Push branch
            push_result = self.api.push_branch(workspace_dir, branch_name)
            if not push_result["success"]:
                return {
                    "success": False,
                    "error": f"Push failed: {push_result['error']}",
                }

            # Create pull request
            pr_title = f"{task_id}: {summary}"
            pr_body = self.api.generate_pr_body(task_id, task_details)

            pr_result = await self.api.create_pull_request_async(
                branch_name, pr_title, pr_body
            )
            if not pr_result["success"]:
                return {
                    "success": False,
                    "error": f"PR creation failed: {pr_result['error']}",
                }

            logger.info(
                f"Workflow completed successfully - PR created: {pr_result['pr_url']}"
            )

            return {
                "success": True,
                "changes": True,
                "commit_message": commit_message,
                "files_changed": commit_result["files_changed"],
                "branch_name": branch_name,
                "pr_number": pr_result["pr_number"],
                "pr_url": pr_result["pr_url"],
            }

        except Exception as e:
            logger.error(f"Failed to complete workflow: {e}")
            return {"success": False, "error": str(e)}

    def complete_workflow(
        self,
        workspace_dir: Path,
        branch_name: str,
        task_id: str,
        task_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for complete_workflow_async."""
        import asyncio

        return asyncio.run(
            self.complete_workflow_async(
                workspace_dir, branch_name, task_id, task_details
            )
        )

    def get_repository_info(self) -> Dict[str, Any]:
        """Get repository configuration information.

        Returns:
            Repository configuration details
        """
        return {
            "repo_owner": self.api.config.repo_owner,
            "repo_name": self.api.config.repo_name,
            "repo_full_name": self.api.config.repo_full_name,
            "base_branch": self.api.config.base_branch,
            "repo_url": self.api.config.repo_url,
            "repo_ssh_url": self.api.config.repo_ssh_url,
        }

    def check_workspace_changes(self, workspace_dir: Path) -> Dict[str, Any]:
        """Check if there are uncommitted changes in the workspace.

        Args:
            workspace_dir: Repository workspace directory

        Returns:
            Information about workspace changes
        """
        try:
            import subprocess

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=workspace_dir,
            )

            if result.returncode != 0:
                return {"success": False, "error": "Failed to check git status"}

            changes = result.stdout.strip()
            if changes:
                change_list = changes.split("\n")
                return {
                    "success": True,
                    "has_changes": True,
                    "num_changes": len(change_list),
                    "changes": change_list,
                }
            else:
                return {
                    "success": True,
                    "has_changes": False,
                    "num_changes": 0,
                    "changes": [],
                }

        except Exception as e:
            logger.error(f"Failed to check workspace changes: {e}")
            return {"success": False, "error": str(e)}


# Convenience functions for direct usage
def setup_workspace(
    target_dir: Path, task_id: str, task_summary: str = "implementation"
) -> Dict[str, Any]:
    """Convenience function to setup repository workspace."""
    tools = GitHubTools()
    return tools.setup_repository_workspace(target_dir, task_id, task_summary)


async def complete_github_workflow_async(
    workspace_dir: Path,
    branch_name: str,
    task_id: str,
    task_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function to complete GitHub workflow."""
    tools = GitHubTools()
    return await tools.complete_workflow_async(
        workspace_dir, branch_name, task_id, task_details
    )


def complete_github_workflow(
    workspace_dir: Path,
    branch_name: str,
    task_id: str,
    task_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Synchronous convenience function to complete GitHub workflow."""
    tools = GitHubTools()
    return tools.complete_workflow(workspace_dir, branch_name, task_id, task_details)
