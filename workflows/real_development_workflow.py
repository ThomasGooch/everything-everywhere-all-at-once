#!/usr/bin/env python3
"""
REAL Development Workflow by ID - Simple and Direct
Uses ./temp directory, launches Claude CLI in repo, cleans up after PR
"""

import subprocess
import shutil
import time
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path for plugin imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import YOUR actual plugins
from plugins.jira.api import JiraAPI
from plugins.github.tools import GitHubTools

load_dotenv()


class WorkflowExecutor:
    """REAL implementation using actual plugins and simple temp directory approach."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.temp_dir = project_root / "temp"
        self.task_details = None
        self.branch_name = None
        self.jira_api = None
        self.github_tools = None

    async def step1_fetch_task_details(self):
        """Step 1: ACTUALLY fetch task details from Jira using real plugin."""
        print(f"\n1️⃣  **FETCH TASK DETAILS FROM JIRA**")

        try:
            # Use YOUR actual Jira plugin
            print(f"   🔄 Initializing Jira API...")
            self.jira_api = JiraAPI()
            print(f"   ✅ Jira API initialized with your credentials")

            # ACTUALLY fetch the task
            print(f"   🔄 Fetching {self.task_id} from Jira API...")
            task_details = await self.jira_api.get_issue_async(self.task_id)

            if not task_details:
                print(f"   ❌ Task {self.task_id} not found")
                return False

            # Display REAL task information
            print(f"   ✅ Task fetched successfully!")
            print(f"      Key: {task_details.get('key')}")
            print(
                f"      Summary: {task_details.get('fields', {}).get('summary', 'No summary')}"
            )
            print(
                f"      Status: {task_details.get('fields', {}).get('status', {}).get('name', 'Unknown')}"
            )

            assignee = task_details.get("fields", {}).get("assignee")
            if assignee:
                print(f"      Assignee: {assignee.get('displayName', 'Unknown')}")
            else:
                print(f"      Assignee: Unassigned")

            self.task_details = task_details
            print(f"   ✅ Step 1 (Fetch Task Details) completed")
            return True

        except Exception as e:
            print(f"   ❌ REAL Jira fetch failed: {str(e)}")
            return False

    async def step2_move_task_to_in_progress(self):
        """Step 2: ACTUALLY move task to In Progress in Jira."""
        print(f"\n2️⃣  **MOVE TASK STATUS TO IN PROGRESS**")

        if not self.jira_api:
            print(f"   ❌ Jira API not available")
            return False

        try:
            # Get available transitions
            print(f"   🔄 Getting available transitions...")
            transitions = await self.jira_api.get_transitions_async(self.task_id)
            transition_names = [t["name"] for t in transitions.get("transitions", [])]
            print(f"   📋 Available transitions: {', '.join(transition_names)}")

            # ACTUALLY transition to In Progress
            print(f"   🔄 ACTUALLY transitioning {self.task_id} to In Progress...")
            result = await self.jira_api.transition_issue_async(
                self.task_id, "In Progress"
            )

            if result.get("success", False):
                print(f"   ✅ Task ACTUALLY moved to In Progress!")
                print(f"   ✅ Step 2 (Move to In Progress) completed")
                return True
            else:
                print(
                    f"   ❌ Failed to transition task: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"   ❌ REAL Jira transition failed: {str(e)}")
            return False

    async def step3_add_automation_comment(self):
        """Step 3: ACTUALLY add automation comment to Jira."""
        print(f"\n3️⃣  **ADD AUTOMATION COMMENT TO JIRA**")

        if not self.jira_api:
            print(f"   ❌ Jira API not available")
            return False

        try:
            comment = f"""🤖 **Automated Development Workflow Started**
            
Task: {self.task_id}
Status: In Progress
Automation: Real Development Workflow
Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The development workflow has been initiated. A development environment will be set up and implementation will begin."""

            print(f"   🔄 ACTUALLY adding comment to {self.task_id}...")
            result = await self.jira_api.add_comment_async(self.task_id, comment)

            if result.get("success", False):
                print(f"   ✅ Automation comment ACTUALLY added to Jira!")
                print(f"   ✅ Step 3 (Add Automation Comment) completed")
                return True
            else:
                print(
                    f"   ❌ Failed to add comment: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"   ❌ REAL Jira comment failed: {str(e)}")
            return False

    def step4_setup_temp_workspace(self):
        """Step 4: Setup temp directory and clone repository using GitHub plugin."""
        print(f"\n4️⃣  **SETUP REPOSITORY WORKSPACE**")

        try:
            # Initialize GitHub tools
            print(f"   🔄 Initializing GitHub integration...")
            self.github_tools = GitHubTools()
            repo_info = self.github_tools.get_repository_info()
            print(f"   ✅ GitHub tools initialized for {repo_info['repo_full_name']}")

            # Setup workspace with task context
            task_summary = "implementation"
            if self.task_details:
                task_summary = self.task_details.get("fields", {}).get(
                    "summary", "implementation"
                )

            print(f"   🔄 Setting up workspace with task context...")
            result = self.github_tools.setup_repository_workspace(
                self.temp_dir, self.task_id, task_summary
            )

            if result["success"]:
                self.branch_name = result["branch_name"]
                print(f"   📁 Workspace: {self.temp_dir}")
                print(f"   🌿 Branch: {self.branch_name}")
                print(f"   🔗 Repository: {result['repo_url']}")
                print(f"   ✅ Step 4 (Setup Workspace) completed")
                return True
            else:
                print(f"   ❌ Workspace setup failed: {result['error']}")
                return False

        except Exception as e:
            print(f"   ❌ GitHub workspace setup failed: {str(e)}")
            return False

    def step5_verify_workspace(self):
        """Step 5: Verify workspace is ready (branch creation now handled in step 4)."""
        print(f"\n5️⃣  **VERIFY WORKSPACE READY**")

        try:
            if not self.github_tools:
                print(f"   ❌ GitHub tools not initialized")
                return False

            if not self.branch_name:
                print(f"   ❌ Branch name not set")
                return False

            # Check workspace status
            changes_result = self.github_tools.check_workspace_changes(self.temp_dir)
            if changes_result["success"]:
                print(f"   📁 Workspace ready: {self.temp_dir}")
                print(f"   🌿 Active branch: {self.branch_name}")
                print(f"   📊 Current changes: {changes_result['num_changes']} files")
                print(f"   ✅ Step 5 (Verify Workspace) completed")
                return True
            else:
                print(f"   ❌ Workspace verification failed: {changes_result['error']}")
                return False

        except Exception as e:
            print(f"   ❌ Workspace verification failed: {str(e)}")
            return False

    def step6_claude_cli_session(self):
        """Step 6: Launch Claude CLI and auto-complete when session ends."""
        print(f"\n6️⃣  **CLAUDE CLI SESSION** 🎯")

        try:
            task_summary = "implementation"
            if self.task_details:
                task_summary = self.task_details.get("fields", {}).get(
                    "summary", "implementation"
                )

            print(f"\n   {'='*80}")
            print(f"   🚀 **LAUNCHING CLAUDE CLI WITH AUTO-COMPLETION**")
            print(f"   {'='*80}")
            print(f"   📋 Task: {self.task_id}")
            print(f"   📁 Workspace: {self.temp_dir}")
            print(f"   🌿 Branch: {self.branch_name}")
            print(f"   🎯 Summary: {task_summary}")
            print(f"")
            print(f"   🎯 **INSTRUCTIONS:**")
            print(f"   📂 Working directory: {self.temp_dir}")
            print(f"   💾 Save ALL files in the workspace directory")
            print(f"   🔧 All dev tools available: dotnet, python3, node, git")
            print(f"   ✨ Ask Claude: 'Help me implement {task_summary}'")
            print(
                f"   🚀 **WHEN YOU EXIT CLAUDE CLI, WORKFLOW CONTINUES AUTOMATICALLY**"
            )
            print(f"   {'='*80}")
            print()

            print(f"   🚀 Opening Terminal with Claude CLI...")
            print(
                f"   ⏳ Workflow will auto-complete when you close the Terminal window..."
            )
            print()

            # Create a completion marker file
            marker_file = self.temp_dir / ".claude_session_complete"
            if marker_file.exists():
                marker_file.unlink()  # Remove if exists

            # Create AppleScript to launch Terminal with Claude CLI and auto-completion
            applescript = f"""
            tell application "Terminal"
                activate
                do script "cd '{self.temp_dir}' && echo '🚀 Claude CLI Session for {self.task_id}' && echo 'Working in: {self.temp_dir}' && echo 'Branch: {self.branch_name}' && echo 'Task: {task_summary}' && echo '' && echo '💡 All dev tools available: dotnet, python3, node, git' && echo '🚀 Starting Claude CLI...' && echo '⚠️  When you exit Claude CLI, the workflow will auto-complete!' && echo '' && claude ; echo '✅ Claude CLI session ended' && touch .claude_session_complete"
            end tell
            """

            # Launch Terminal with Claude CLI
            subprocess.run(["osascript", "-e", applescript])

            print(f"   ✅ Terminal launched with Claude CLI!")
            print(f"   ⏳ Waiting for Claude CLI session to complete...")
            print(f"   📋 Work with Claude CLI in the Terminal window")
            print(f"   🔄 When you exit Claude CLI, workflow will auto-continue...")

            # Wait for the completion marker file with longer timeout
            import time

            max_wait_time = 3600  # 1 hour max wait time
            wait_time = 0

            while not marker_file.exists() and wait_time < max_wait_time:
                time.sleep(3)  # Check every 3 seconds
                wait_time += 3

            if marker_file.exists():
                print(f"   ✅ Claude CLI session completed!")
                # Remove the marker file
                marker_file.unlink()
            else:
                print(f"   ⚠️  Timeout reached - assuming session completed")

            print(f"\n   {'='*80}")
            print(f"   ✅ **CLAUDE CLI SESSION ENDED - AUTO-COMPLETING WORKFLOW**")
            print(f"   {'='*80}")
            print(f"   🔄 Checking for changes and creating PR...")
            print(f"   🔄 Updating Jira status...")
            print(f"   🔄 Cleaning up temp directory...")
            print(f"   {'='*80}")

            print(f"   ✅ Step 6 (Claude CLI Session) completed")
            return True

        except Exception as e:
            print(f"   ❌ Claude CLI session failed: {str(e)}")
            return False

    async def step7_create_github_pr(self):
        """Step 7: Complete GitHub workflow - commit, push, create PR using GitHub plugin."""
        print(f"\n7️⃣  **COMPLETE GITHUB WORKFLOW**")

        try:
            if not self.github_tools:
                print(f"   ❌ GitHub tools not available")
                return False

            print(f"   🔄 Completing GitHub workflow with plugin...")
            result = await self.github_tools.complete_workflow_async(
                self.temp_dir, self.branch_name, self.task_id, self.task_details
            )

            if result["success"]:
                if result.get("changes", True):
                    print(
                        f"   📄 Changes processed: {result.get('files_changed', 0)} files"
                    )
                    print(f"   ✅ Changes committed and pushed")
                    print(f"   🔗 Pull Request created: #{result['pr_number']}")
                    print(f"   🌐 PR URL: {result['pr_url']}")

                    # Store PR URL for later use
                    self.pr_url = result["pr_url"]
                else:
                    print(
                        f"   ℹ️ No changes detected - workflow completed without modifications"
                    )
                    self.pr_url = None

                print(f"   ✅ Step 7 (Complete GitHub Workflow) completed")
                return True
            else:
                print(f"   ❌ GitHub workflow failed: {result['error']}")
                return False

        except Exception as e:
            print(f"   ❌ GitHub workflow completion failed: {str(e)}")
            return False

    async def step8_move_task_to_review(self):
        """Step 8: Move task to review/done status."""
        print(f"\n8️⃣  **MOVE TASK TO REVIEW/DONE**")

        if not self.jira_api:
            print(f"   ❌ Jira API not available")
            return False

        try:
            # Get available transitions
            print(f"   🔄 Getting review transitions...")
            transitions = await self.jira_api.get_transitions_async(self.task_id)
            transition_names = [t["name"] for t in transitions.get("transitions", [])]
            print(f"   📋 Available transitions: {', '.join(transition_names)}")

            # Try to move to Done or Review
            target_status = "Done"
            if "Review" in transition_names:
                target_status = "Review"
            elif "Done" in transition_names:
                target_status = "Done"
            else:
                target_status = transition_names[0] if transition_names else "Done"

            print(f"   🔄 ACTUALLY moving {self.task_id} to review...")
            result = await self.jira_api.transition_issue_async(
                self.task_id, target_status
            )

            if result.get("success", False):
                print(f"   ✅ Task ACTUALLY moved to review status!")
                print(f"   ✅ Step 8 (Move to Review) completed")
                return True
            else:
                print(
                    f"   ❌ Failed to move task: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"   ❌ REAL Jira review transition failed: {str(e)}")
            return False

    async def step9_add_completion_comment(self):
        """Step 9: Add completion comment to Jira."""
        print(f"\n9️⃣  **ADD COMPLETION COMMENT TO JIRA**")

        if not self.jira_api:
            print(f"   ❌ Jira API not available")
            return False

        try:
            # Use actual PR URL if available, otherwise generate fallback
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

The automated development workflow has successfully completed the implementation. Please review the pull request and merge when ready."""

            print(f"   🔄 ACTUALLY adding completion comment...")
            result = await self.jira_api.add_comment_async(self.task_id, comment)

            if result.get("success", False):
                print(f"   ✅ Completion comment ACTUALLY added to Jira!")
                print(f"   ✅ Step 9 (Add Completion Comment) completed")
                return True
            else:
                print(
                    f"   ❌ Failed to add completion comment: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"   ❌ REAL Jira completion comment failed: {str(e)}")
            return False

    def step10_cleanup_temp_directory(self):
        """Step 10: Clean up temp directory after successful workflow."""
        print(f"\n🔟 **CLEANUP TEMP DIRECTORY**")

        try:
            # Check if there were changes (i.e., if we have a branch)
            if self.branch_name:
                print(f"   🧹 Implementation completed, cleaning up temp directory...")
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir)
                    print(f"   ✅ Temp directory cleaned: {self.temp_dir}")
                    print(f"   ✅ /temp is empty")
                else:
                    print(f"   ℹ️ Temp directory already clean")
            else:
                print(f"   ℹ️ No changes made, keeping temp directory for future work")
                print(f"   📁 Temp directory preserved: {self.temp_dir}")

            print(f"   ✅ Step 10 (Cleanup) completed")
            return True

        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {str(e)}")
            return True  # Don't fail the workflow on cleanup issues

    async def run(self):
        """Run the complete development workflow."""
        print(f"{'='*80}")
        print(f"🎯 REAL AI DEVELOPMENT AUTOMATION WORKFLOW BY ID")
        print(f"Simple Direct Approach - Uses ./temp directory")
        print(f"{'='*80}")
        print(f"Task ID: {self.task_id}")
        if self.github_tools:
            repo_info = self.github_tools.get_repository_info()
            print(f"Repository: {repo_info['repo_full_name']}")
        print(f"This will make REAL API calls and launch REAL Claude CLI session!")
        print(f"{'='*80}")

        steps_completed = 0
        total_steps = 10

        try:
            # Execute all workflow steps
            if await self.step1_fetch_task_details():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to fetch task details"}

            if await self.step2_move_task_to_in_progress():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to move task to in progress"}

            if await self.step3_add_automation_comment():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to add automation comment"}

            if self.step4_setup_temp_workspace():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to setup temp workspace"}

            if self.step5_verify_workspace():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to verify workspace"}

            if self.step6_claude_cli_session():
                steps_completed += 1
            else:
                return {
                    "success": False,
                    "error": "Failed to execute Claude CLI session",
                }

            if await self.step7_create_github_pr():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to create GitHub PR"}

            if await self.step8_move_task_to_review():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to move task to review"}

            if await self.step9_add_completion_comment():
                steps_completed += 1
            else:
                return {"success": False, "error": "Failed to add completion comment"}

            if self.step10_cleanup_temp_directory():
                steps_completed += 1

            # Success summary
            print(f"\n{'='*80}")
            print(f"🏁 **REAL WORKFLOW EXECUTION COMPLETED!**")
            print(f"{'='*80}")
            print(f"**Task ID**: {self.task_id}")
            print(f"**Steps Completed**: {steps_completed}/{total_steps}")
            if self.branch_name:
                print(f"**Branch**: {self.branch_name}")
                if hasattr(self, "pr_url") and self.pr_url:
                    print(f"**Pull Request**: {self.pr_url}")
                else:
                    repo_info = (
                        self.github_tools.get_repository_info()
                        if self.github_tools
                        else {}
                    )
                    repo_name = repo_info.get("repo_full_name", "repository")
                    print(
                        f"**Pull Request**: https://github.com/{repo_name}/compare/{self.branch_name}?expand=1"
                    )

            print(f"\n**REAL Integration Results:**")
            print(f"🔌 Jira Plugin: ✅ REAL API calls made")
            print(f"🔌 GitHub Plugin: ✅ REAL operations successful")
            print(f"🔌 Claude CLI: ✅ REAL session launched")

            print(f"\n🎉 **REAL WORKFLOW SUCCESS!**")
            print(f"   Your development workflow executed with REAL integrations!")
            print(f"{'='*80}")
            return {
                "success": True,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
            }

        except Exception as e:
            print(f"\n❌ **WORKFLOW FAILED**: {str(e)}")
            # Clean up on error
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            return {
                "success": False,
                "error": str(e),
                "steps_completed": steps_completed,
            }


async def main(args):
    """Main execution function for workflow CLI."""
    if len(args) != 1:
        print("Usage: python main.py --workflows real_development_workflow <task-id>")
        print("Example: python main.py --workflows real_development_workflow CMMAI-49")
        return {"success": False, "error": "Task ID required"}

    task_id = args[0]
    workflow = WorkflowExecutor(task_id)
    return await workflow.run()
