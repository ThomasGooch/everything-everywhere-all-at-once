#!/usr/bin/env python3
"""
Complete Workflow - Handles interrupted workflows
Completes remaining automation steps with robust error recovery
"""

import asyncio
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for plugin imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from plugins.github.tools import GitHubTools

# Import YOUR actual plugins
from plugins.jira.api import JiraAPI

load_dotenv()


class WorkflowExecutor:
    """Manual completion utility for interrupted workflows."""

    def __init__(self, task_id: str, branch_name: str = None):
        self.task_id = task_id
        self.branch_name = branch_name
        self.temp_dir = project_root / "temp"
        self.jira_api = None
        self.task_details = None
        self.github_tools = None

    async def initialize_jira(self):
        """Initialize Jira API connection."""
        try:
            self.jira_api = JiraAPI()

            # Fetch task details for context
            task_details = await self.jira_api.get_issue_async(self.task_id)
            if task_details:
                self.task_details = task_details
                print(f"✅ Connected to Jira - Task: {self.task_id}")
                return True
            else:
                print(f"❌ Could not fetch task details for {self.task_id}")
                return False

        except Exception as e:
            print(f"❌ Failed to initialize Jira API: {e}")
            return False

    async def complete_github_operations(self):
        """Complete GitHub operations using GitHub plugin - commit, push, create PR."""
        print(f"\n📁 **COMPLETING GITHUB OPERATIONS**")

        if not self.temp_dir.exists():
            print(f"❌ Temp directory not found: {self.temp_dir}")
            return False

        try:
            # Initialize GitHub tools
            self.github_tools = GitHubTools()

            # Determine branch name if not provided
            if not self.branch_name:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    cwd=self.temp_dir,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.branch_name = result.stdout.strip()
                    print(f"🌿 Detected current branch: {self.branch_name}")
                else:
                    print(f"❌ Could not determine current branch")
                    return False

            # Complete workflow using GitHub plugin
            print(f"🔄 Completing workflow with GitHub plugin...")
            result = await self.github_tools.complete_workflow_async(
                self.temp_dir, self.branch_name, self.task_id, self.task_details
            )

            if result["success"]:
                if result.get("changes", True):
                    print(
                        f"📄 Changes processed: {result.get('files_changed', 0)} files"
                    )
                    print(f"✅ Changes committed and pushed")
                    print(f"🔗 Pull Request created: #{result['pr_number']}")
                    print(f"🌐 PR URL: {result['pr_url']}")

                    # Store PR URL for Jira comment
                    self.pr_url = result["pr_url"]
                else:
                    print(f"ℹ️ No changes detected")
                    self.pr_url = None

                return True
            else:
                print(f"❌ GitHub workflow failed: {result['error']}")
                return False

        except Exception as e:
            print(f"❌ GitHub operations failed: {e}")
            return False

    async def complete_jira_operations(self):
        """Complete Jira operations - move to review, add completion comment."""
        print(f"\n📋 **COMPLETING JIRA OPERATIONS**")

        if not self.jira_api:
            print(f"❌ Jira API not available")
            return False

        try:
            # Move to review/done
            transitions = await self.jira_api.get_transitions_async(self.task_id)
            transition_names = [t["name"] for t in transitions.get("transitions", [])]

            target_status = "Done"
            if "Review" in transition_names:
                target_status = "Review"
            elif "Done" in transition_names:
                target_status = "Done"
            else:
                target_status = transition_names[0] if transition_names else "Done"

            result = await self.jira_api.transition_issue_async(
                self.task_id, target_status
            )
            if result.get("success", False):
                print(f"✅ Task moved to {target_status}")

            # Add completion comment
            pr_url = getattr(self, "pr_url", None)
            if not pr_url and self.branch_name:
                # Fallback URL generation
                repo_info = (
                    self.github_tools.get_repository_info() if self.github_tools else {}
                )
                repo_name = repo_info.get("repo_full_name", "repository")
                pr_url = f"https://github.com/{repo_name}/compare/{self.branch_name}?expand=1"

            comment = f"""✅ **Automated Development Workflow Completed**

Task: {self.task_id}
Status: Implementation Complete
Branch: {self.branch_name or 'main'}
Pull Request: {pr_url or 'No PR created'}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The automated development workflow has successfully completed the implementation. 
Please review the pull request and merge when ready."""

            result = await self.jira_api.add_comment_async(self.task_id, comment)
            if result.get("success", False):
                print(f"✅ Completion comment added to Jira!")

            return True

        except Exception as e:
            print(f"❌ Jira operations failed: {e}")
            return False

    def cleanup_temp_directory(self):
        """Clean up temp directory after completion."""
        print(f"\n🧹 **CLEANING UP TEMP DIRECTORY**")

        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"✅ Temp directory cleaned: {self.temp_dir}")
                print(f"✅ /temp is empty")
            else:
                print(f"ℹ️ Temp directory already clean")

            return True

        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
            return True  # Don't fail on cleanup issues

    async def run(self):
        """Run the completion workflow."""
        print(f"{'='*80}")
        print(f"🔧 WORKFLOW COMPLETION UTILITY")
        print(f"{'='*80}")
        print(f"Task ID: {self.task_id}")
        if self.branch_name:
            print(f"Branch: {self.branch_name}")
        print(f"This will complete any remaining workflow steps")
        print(f"{'='*80}")

        try:
            # Initialize Jira connection
            if not await self.initialize_jira():
                return {"success": False, "error": "Failed to initialize Jira API"}

            # Complete GitHub operations
            if not await self.complete_github_operations():
                return {
                    "success": False,
                    "error": "Failed to complete GitHub operations",
                }

            # Complete Jira operations
            if not await self.complete_jira_operations():
                return {"success": False, "error": "Failed to complete Jira operations"}

            # Cleanup
            self.cleanup_temp_directory()

            print(f"\n{'='*80}")
            print(f"✅ **WORKFLOW COMPLETION SUCCESSFUL!**")
            print(f"{'='*80}")
            print(f"Task: {self.task_id}")
            if self.branch_name:
                print(f"Branch: {self.branch_name}")
                if hasattr(self, "pr_url") and self.pr_url:
                    print(f"PR: {self.pr_url}")
                else:
                    repo_info = (
                        self.github_tools.get_repository_info()
                        if self.github_tools
                        else {}
                    )
                    repo_name = repo_info.get("repo_full_name", "repository")
                    print(
                        f"PR: https://github.com/{repo_name}/compare/{self.branch_name}?expand=1"
                    )
            print(f"{'='*80}")

            return {"success": True}

        except Exception as e:
            print(f"❌ Completion failed: {e}")
            return {"success": False, "error": str(e)}


async def main(args):
    """Main execution function for completion workflow."""
    if len(args) < 1:
        print(
            "Usage: python main.py --workflows complete_workflow <task-id> [branch-name]"
        )
        print(
            "Example: python main.py --workflows complete_workflow CMMAI-49 feature-branch"
        )
        return {"success": False, "error": "Task ID required"}

    task_id = args[0]
    branch_name = args[1] if len(args) > 1 else None

    workflow = WorkflowExecutor(task_id, branch_name)
    return await workflow.run()
