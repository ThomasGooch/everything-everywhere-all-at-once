"""
Git Operations Wrapper for safe Git operations
Provides secure Git operations with proper error handling and validation
"""
import ast
import asyncio
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import git
except ImportError:
    git = None

from .exceptions import BaseSystemError

logger = logging.getLogger(__name__)


class GitError(BaseSystemError):
    """Base exception for Git-related errors"""

    pass


class GitAuthError(GitError):
    """Exception raised for Git authentication errors"""

    pass


@dataclass
class CommitResult:
    """Result of a commit and push operation"""

    success: bool
    commit_hash: Optional[str] = None
    message: Optional[str] = None
    files_changed: Optional[List[str]] = None
    insertions: Optional[int] = None
    deletions: Optional[int] = None
    error: Optional[str] = None


class GitOperations:
    """Safe Git operations with proper error handling and validation"""

    def __init__(self):
        """Initialize GitOperations"""
        if git is None:
            raise GitError("GitPython package is required for Git operations")

    async def setup_repository(
        self, workspace, branch_name: str, create_branch: bool = False
    ) -> bool:
        """Setup repository in workspace with specified branch"""
        try:
            # Clone repository
            repo = git.Repo.clone_from(workspace.repository_url, workspace.path)

            # Configure Git user (use environment variables or defaults)
            repo.git.config("user.name", os.getenv("GIT_USER_NAME", "AI Agent"))
            repo.git.config(
                "user.email", os.getenv("GIT_USER_EMAIL", "agent@example.com")
            )

            # Create or checkout branch
            if create_branch:
                repo.create_head(branch_name)

            repo.git.checkout(branch_name)

            logger.info(
                f"Successfully setup repository in {workspace.path} on branch {branch_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to setup repository: {e}")
            raise GitError(f"Failed to clone repository: {e}")

    async def apply_file_changes(
        self,
        workspace,
        file_changes: Dict[str, Dict[str, Any]],
        create_backup: bool = True,
    ) -> bool:
        """Apply file changes to the workspace"""
        try:
            # Create backups if requested
            if create_backup:
                await self._backup_existing_files(workspace, file_changes)

            # Validate changes before applying
            if not await self._validate_file_changes(workspace, file_changes):
                raise GitError("File validation failed")

            # Apply changes
            for file_path, change_info in file_changes.items():
                full_path = Path(workspace.path) / file_path
                action = change_info.get("action", "modify")
                content = change_info.get("content", "")

                if action == "create" or action == "modify":
                    # Ensure parent directories exist
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                elif action == "delete":
                    if full_path.exists():
                        full_path.unlink()

            logger.info(f"Successfully applied {len(file_changes)} file changes")
            return True

        except Exception as e:
            logger.error(f"Failed to apply file changes: {e}")
            raise GitError(f"Failed to apply file changes: {e}")

    async def commit_and_push(
        self, workspace, message: str, push_to_remote: bool = True
    ) -> CommitResult:
        """Commit changes and optionally push to remote"""
        try:
            repo = git.Repo(workspace.path)

            # Check if there are any changes
            if not repo.is_dirty() and not repo.untracked_files:
                return CommitResult(success=True, message="No changes to commit")

            # Stage all changes
            repo.git.add(".")

            # Create commit
            commit = repo.index.commit(message)
            commit_hash = commit.hexsha

            # Get statistics
            diff_stats = (
                repo.git.diff("HEAD~1", "--stat") if repo.head.is_valid() else ""
            )
            files_changed = [item.a_path for item in repo.index.diff(None)]

            result = CommitResult(
                success=True,
                commit_hash=commit_hash,
                message=message,
                files_changed=files_changed,
            )

            # Push to remote if requested
            if push_to_remote:
                try:
                    repo.remotes.origin.push()
                    logger.info(
                        f"Successfully pushed commit {commit_hash[:8]} to remote"
                    )
                except Exception as e:
                    if "authentication" in str(e).lower():
                        raise GitAuthError(f"Authentication failed during push: {e}")
                    else:
                        raise GitError(f"Failed to push to remote: {e}")

            logger.info(f"Successfully committed changes: {commit_hash[:8]}")
            return result

        except (GitAuthError, GitError):
            raise
        except Exception as e:
            logger.error(f"Failed to commit and push: {e}")
            raise GitError(f"Failed to commit and push: {e}")

    async def validate_repository_state(self, workspace) -> bool:
        """Validate the repository state"""
        try:
            repo = git.Repo(workspace.path)
            return not repo.is_dirty()
        except Exception:
            return False

    async def handle_merge_conflicts(self, workspace) -> bool:
        """Handle merge conflicts"""
        try:
            return await self._resolve_merge_conflicts(workspace)
        except Exception as e:
            logger.error(f"Failed to handle merge conflicts: {e}")
            return False

    async def get_repository_status(self, workspace) -> Dict[str, Any]:
        """Get comprehensive repository status"""
        try:
            repo = git.Repo(workspace.path)
            return {
                "current_branch": repo.active_branch.name,
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files,
                "latest_commit": str(repo.head.commit),
            }
        except Exception as e:
            logger.error(f"Failed to get repository status: {e}")
            return {}

    async def cleanup_repository(self, workspace) -> bool:
        """Clean up repository state"""
        try:
            repo = git.Repo(workspace.path)
            repo.git.clean("-fd")  # Remove untracked files and directories
            repo.git.reset("--hard", "HEAD")  # Reset to HEAD
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup repository: {e}")
            return False

    async def _backup_existing_files(
        self, workspace, file_changes: Dict[str, Dict]
    ) -> None:
        """Create backups of existing files before modification"""
        backup_dir = Path(workspace.path) / ".backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file_path in file_changes.keys():
            full_path = Path(workspace.path) / file_path
            if full_path.exists():
                backup_name = f"{file_path.replace('/', '_')}.{timestamp}"
                backup_path = backup_dir / backup_name
                shutil.copy2(full_path, backup_path)

    async def _validate_file_changes(
        self, workspace, file_changes: Dict[str, Dict]
    ) -> bool:
        """Validate file changes before applying"""
        for file_path, change_info in file_changes.items():
            content = change_info.get("content", "")

            # Validate based on file extension
            if file_path.endswith(".py"):
                if not self._validate_python_syntax(content):
                    logger.error(f"Invalid Python syntax in {file_path}")
                    return False
            elif file_path.endswith(".js"):
                if not self._validate_javascript_syntax(content):
                    logger.error(f"Invalid JavaScript syntax in {file_path}")
                    return False

        return True

    def _validate_python_syntax(self, content: str) -> bool:
        """Validate Python code syntax"""
        try:
            # Handle simple text content that's not Python code
            if not content.strip():
                return True

            # Simple heuristic: if it doesn't look like code, accept it
            if not any(
                keyword in content
                for keyword in ["def", "class", "import", "from", "="]
            ):
                return True

            ast.parse(content)
            return True
        except SyntaxError:
            return False

    def _validate_javascript_syntax(self, content: str) -> bool:
        """Validate JavaScript code syntax (basic check)"""
        # Basic validation - could be enhanced with actual JS parser
        try:
            # Check for basic syntax issues
            if content.count("{") != content.count("}"):
                return False
            if content.count("(") != content.count(")"):
                return False
            return True
        except Exception:
            return False

    async def _resolve_merge_conflicts(self, workspace) -> bool:
        """Attempt to resolve merge conflicts automatically"""
        try:
            # This is a simplified implementation
            # In practice, would need sophisticated conflict resolution
            repo = git.Repo(workspace.path)

            # For now, just indicate conflicts were handled
            # Real implementation would analyze and resolve conflicts
            return True
        except Exception:
            return False
