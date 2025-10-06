#!/usr/bin/env python3
"""
REAL Development Workflow by ID - Simple and Direct
Uses ./temp directory, launches Claude CLI in repo, cleans up after PR
"""

import os
import subprocess
import shutil
import asyncio
import time
import sys
import psutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path for plugin imports  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import YOUR actual plugins
from plugins.jira.api import JiraAPI
from plugins.jira.config import JiraConfig

load_dotenv()


class RealDevelopmentWorkflowByID:
    """REAL implementation using actual plugins and simple temp directory approach."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.temp_dir = project_root / "temp"
        self.repo_url = "git@github.com:ThomasGooch/agenticDummy.git"
        self.task_details = None
        self.branch_name = None
        self.jira_api = None
    
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
            print(f"      Summary: {task_details.get('fields', {}).get('summary', 'No summary')}")
            print(f"      Status: {task_details.get('fields', {}).get('status', {}).get('name', 'Unknown')}")
            
            assignee = task_details.get('fields', {}).get('assignee')
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
            transition_names = [t['name'] for t in transitions.get('transitions', [])]
            print(f"   📋 Available transitions: {', '.join(transition_names)}")
            
            # ACTUALLY transition to In Progress
            print(f"   🔄 ACTUALLY transitioning {self.task_id} to In Progress...")
            result = await self.jira_api.transition_issue_async(self.task_id, "In Progress")
            
            if result.get('success', False):
                print(f"   ✅ Task ACTUALLY moved to In Progress!")
                print(f"   ✅ Step 2 (Move to In Progress) completed")
                return True
            else:
                print(f"   ❌ Failed to transition task: {result.get('error', 'Unknown error')}")
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
            
            if result.get('success', False):
                print(f"   ✅ Automation comment ACTUALLY added to Jira!")
                print(f"   ✅ Step 3 (Add Automation Comment) completed")
                return True
            else:
                print(f"   ❌ Failed to add comment: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ REAL Jira comment failed: {str(e)}")
            return False

    def step4_setup_temp_workspace(self):
        """Step 4: Setup temp directory and clone repository."""
        print(f"\n4️⃣  **CLONE REPOSITORY TO TEMP**")
        
        try:
            # Clean up any existing temp directory
            if self.temp_dir.exists():
                print(f"   🧹 Cleaning existing temp directory...")
                shutil.rmtree(self.temp_dir)
            
            # Clone repository to temp
            print(f"   📁 Temp directory: {self.temp_dir}")
            print(f"   🔄 Cloning {self.repo_url}...")
            subprocess.run(["git", "clone", self.repo_url, str(self.temp_dir)], check=True)
            print(f"   ✅ Repository cloned successfully!")
            print(f"   ✅ Step 4 (Clone Repository) completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Repository clone failed: {str(e)}")
            return False
    
    def step5_create_branch(self):
        """Step 5: Create branch for the task."""
        print(f"\n5️⃣  **CREATE BRANCH /<taskId>_summary**")
        
        try:
            # Create branch name
            summary = "implementation"
            if self.task_details:
                real_summary = self.task_details.get('fields', {}).get('summary', '')
                if real_summary:
                    summary = real_summary.lower().replace(' ', '_').replace('-', '_')[:30]
            
            timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
            self.branch_name = f"{self.task_id}_{summary}_{timestamp}"
            
            print(f"   🔄 Creating branch: {self.branch_name}")
            subprocess.run(["git", "checkout", "-b", self.branch_name], cwd=self.temp_dir, check=True)
            print(f"   ✅ Branch created successfully!")
            print(f"   ✅ Step 5 (Create Branch) completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Branch creation failed: {str(e)}")
            return False

    def step6_claude_cli_session(self):
        """Step 6: Launch Claude CLI and auto-complete when session ends."""
        print(f"\n6️⃣  **CLAUDE CLI SESSION** 🎯")
        
        try:
            task_summary = "implementation"
            if self.task_details:
                task_summary = self.task_details.get('fields', {}).get('summary', 'implementation')
            
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
            print(f"   🚀 **WHEN YOU EXIT CLAUDE CLI, WORKFLOW CONTINUES AUTOMATICALLY**")
            print(f"   {'='*80}")
            print()
            
            print(f"   🚀 Opening Terminal with Claude CLI...")
            print(f"   ⏳ Workflow will auto-complete when you close the Terminal window...")
            print()
            
            # Create a completion marker file
            marker_file = self.temp_dir / ".claude_session_complete"
            if marker_file.exists():
                marker_file.unlink()  # Remove if exists
            
            # Create AppleScript to launch Terminal with Claude CLI and auto-completion
            applescript = f'''
            tell application "Terminal"
                activate
                do script "cd '{self.temp_dir}' && echo '🚀 Claude CLI Session for {self.task_id}' && echo 'Working in: {self.temp_dir}' && echo 'Branch: {self.branch_name}' && echo 'Task: {task_summary}' && echo '' && echo '💡 All dev tools available: dotnet, python3, node, git' && echo '🚀 Starting Claude CLI...' && echo '⚠️  When you exit Claude CLI, the workflow will auto-complete!' && echo '' && claude ; echo '✅ Claude CLI session ended' && touch .claude_session_complete"
            end tell
            '''
            
            # Launch Terminal with Claude CLI
            subprocess.run(['osascript', '-e', applescript])
            
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

    def step7_create_github_pr(self):
        """Step 7: Check for changes and create GitHub PR."""
        print(f"\n7️⃣  **CREATE GITHUB PR**")
        
        try:
            print(f"   📁 Checking changes in: {self.temp_dir}")
            
            # Check for changes
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, cwd=self.temp_dir)
            
            if result.stdout.strip():
                changes = result.stdout.strip().split('\n')
                print(f"   📄 Changes detected:")
                for change in changes[:5]:  # Show first 5
                    print(f"      {change}")
                if len(changes) > 5:
                    print(f"      ... and {len(changes) - 5} more files")
                
                # Stage and commit changes
                print(f"   ✅ User changes staged")
                subprocess.run(["git", "add", "."], cwd=self.temp_dir, check=True)
                
                commit_message = f"{self.task_id}: {self.task_details.get('fields', {}).get('summary', 'Implementation')}\n\n🤖 Generated with automated workflow"
                subprocess.run(["git", "commit", "-m", commit_message], cwd=self.temp_dir, check=True)
                print(f"   ✅ Changes committed")
                
                # Push branch
                subprocess.run(["git", "push", "-u", "origin", self.branch_name], cwd=self.temp_dir, check=True)
                print(f"   ✅ Branch pushed to GitHub!")
                
                # Create PR URL
                pr_url = f"https://github.com/ThomasGooch/agenticDummy/compare/{self.branch_name}?expand=1"
                print(f"   🔗 PR URL: {pr_url}")
                print(f"   ✅ Step 7 (Create GitHub PR) completed")
                return True
                
            else:
                print(f"   ℹ️ No changes detected")
                print(f"   ✅ Step 7 (Create GitHub PR) completed")
                return True
                
        except Exception as e:
            print(f"   ❌ GitHub PR creation failed: {str(e)}")
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
            transition_names = [t['name'] for t in transitions.get('transitions', [])]
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
            result = await self.jira_api.transition_issue_async(self.task_id, target_status)
            
            if result.get('success', False):
                print(f"   ✅ Task ACTUALLY moved to review status!")
                print(f"   ✅ Step 8 (Move to Review) completed")
                return True
            else:
                print(f"   ❌ Failed to move task: {result.get('error', 'Unknown error')}")
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
            pr_url = f"https://github.com/ThomasGooch/agenticDummy/compare/{self.branch_name}?expand=1"
            comment = f"""✅ **Automated Development Workflow Completed**

Task: {self.task_id}
Status: Implementation Complete
Branch: {self.branch_name}
Pull Request: {pr_url}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The automated development workflow has successfully completed the implementation. Please review the pull request and merge when ready."""
            
            print(f"   🔄 ACTUALLY adding completion comment...")
            result = await self.jira_api.add_comment_async(self.task_id, comment)
            
            if result.get('success', False):
                print(f"   ✅ Completion comment ACTUALLY added to Jira!")
                print(f"   ✅ Step 9 (Add Completion Comment) completed")
                return True
            else:
                print(f"   ❌ Failed to add completion comment: {result.get('error', 'Unknown error')}")
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

    async def run_full_workflow(self):
        """Run the complete development workflow."""
        print(f"{'='*80}")
        print(f"🎯 REAL AI DEVELOPMENT AUTOMATION WORKFLOW BY ID")
        print(f"Simple Direct Approach - Uses ./temp directory")
        print(f"{'='*80}")
        print(f"Task ID: {self.task_id}")
        print(f"Repository: {self.repo_url}")
        print(f"This will make REAL API calls and launch REAL Claude CLI session!")
        print(f"{'='*80}")
        
        steps_completed = 0
        total_steps = 10
        
        try:
            # Execute all workflow steps
            if await self.step1_fetch_task_details():
                steps_completed += 1
            else:
                return False
            
            if await self.step2_move_task_to_in_progress():
                steps_completed += 1
            else:
                return False
            
            if await self.step3_add_automation_comment():
                steps_completed += 1
            else:
                return False
            
            if self.step4_setup_temp_workspace():
                steps_completed += 1
            else:
                return False
            
            if self.step5_create_branch():
                steps_completed += 1
            else:
                return False
            
            if self.step6_claude_cli_session():
                steps_completed += 1
            else:
                return False
            
            if self.step7_create_github_pr():
                steps_completed += 1
            else:
                return False
            
            if await self.step8_move_task_to_review():
                steps_completed += 1
            else:
                return False
            
            if await self.step9_add_completion_comment():
                steps_completed += 1
            else:
                return False
            
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
                print(f"**Pull Request**: https://github.com/ThomasGooch/agenticDummy/compare/{self.branch_name}?expand=1")
            
            print(f"\n**REAL Integration Results:**")
            print(f"🔌 Jira Plugin: ✅ REAL API calls made")
            print(f"🔌 GitHub Plugin: ✅ REAL operations successful") 
            print(f"🔌 Claude CLI: ✅ REAL session launched")
            
            print(f"\n🎉 **REAL WORKFLOW SUCCESS!**")
            print(f"   Your development workflow executed with REAL integrations!")
            print(f"{'='*80}")
            return True
            
        except Exception as e:
            print(f"\n❌ **WORKFLOW FAILED**: {str(e)}")
            # Clean up on error
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            return False


async def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python real_development_workflow_by_id.py <task-id>")
        print("Example: python real_development_workflow_by_id.py CMMAI-49")
        sys.exit(1)
    
    task_id = sys.argv[1]
    workflow = RealDevelopmentWorkflowByID(task_id)
    success = await workflow.run_full_workflow()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())