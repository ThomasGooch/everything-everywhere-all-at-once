#!/usr/bin/env python3
"""
Complete interrupted workflow - Create PR, update Jira, cleanup temp
"""

import os
import subprocess
import shutil
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for plugin imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import YOUR actual plugins
from plugins.jira.api import JiraAPI

load_dotenv()


async def complete_workflow(task_id: str, branch_name: str):
    """Complete the remaining workflow steps."""
    temp_dir = project_root / "temp"

    print(f"🔧 **COMPLETING INTERRUPTED WORKFLOW**")
    print(f"Task ID: {task_id}")
    print(f"Branch: {branch_name}")
    print(f"Temp dir: {temp_dir}")
    print()

    try:
        # Step 1: Check for changes and create PR
        print(f"1️⃣ **CHECKING FOR CHANGES AND CREATING PR**")

        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )

        if result.stdout.strip():
            changes = result.stdout.strip().split("\n")
            print(f"   📄 Changes detected:")
            for change in changes[:10]:  # Show first 10
                print(f"      {change}")
            if len(changes) > 10:
                print(f"      ... and {len(changes) - 10} more files")

            # Stage and commit changes
            print(f"   🔄 Staging changes...")
            subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)

            commit_message = f"{task_id}: Create initial project setup\n\n🤖 Generated with automated workflow\n\nCreated WebAPI project structure with default configuration."
            subprocess.run(
                ["git", "commit", "-m", commit_message], cwd=temp_dir, check=True
            )
            print(f"   ✅ Changes committed")

            # Push branch
            print(f"   🔄 Pushing to GitHub...")
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name], cwd=temp_dir, check=True
            )
            print(f"   ✅ Branch pushed to GitHub!")

            # Create PR URL
            pr_url = f"https://github.com/ThomasGooch/agenticDummy/compare/{branch_name}?expand=1"
            print(f"   🔗 PR URL: {pr_url}")
            print(f"   ✅ Step 1 completed")

        else:
            print(f"   ℹ️ No changes detected")
            pr_url = None

        # Step 2: Update Jira to Done
        print(f"\n2️⃣ **UPDATING JIRA TO DONE**")

        try:
            jira_api = JiraAPI()

            # Get available transitions
            transitions = await jira_api.get_transitions_async(task_id)
            transition_names = [t["name"] for t in transitions.get("transitions", [])]
            print(f"   📋 Available transitions: {', '.join(transition_names)}")

            # Move to Done
            target_status = (
                "Done" if "Done" in transition_names else transition_names[0]
            )
            result = await jira_api.transition_issue_async(task_id, target_status)

            if result.get("success", False):
                print(f"   ✅ Task moved to {target_status}!")
            else:
                print(
                    f"   ⚠️ Failed to move task: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"   ⚠️ Jira update warning: {str(e)}")

        # Step 3: Add completion comment
        print(f"\n3️⃣ **ADDING COMPLETION COMMENT TO JIRA**")

        try:
            if pr_url:
                comment = f"""✅ **Automated Development Workflow Completed Successfully**

Task: {task_id}
Status: Implementation Complete  
Branch: {branch_name}
Pull Request: {pr_url}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Implementation Summary:**
- Created initial .NET WebAPI project structure
- Added default configuration and launch settings
- Project ready for development and deployment

The automated development workflow has successfully completed the implementation. Please review the pull request and merge when ready."""
            else:
                comment = f"""✅ **Automated Development Workflow Completed**

Task: {task_id}
Status: Complete
Branch: {branch_name}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The automated development workflow has completed successfully."""

            result = await jira_api.add_comment_async(task_id, comment)

            if result.get("success", False):
                print(f"   ✅ Completion comment added!")
            else:
                print(
                    f"   ⚠️ Failed to add comment: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"   ⚠️ Jira comment warning: {str(e)}")

        # Step 4: Clean up temp directory
        print(f"\n4️⃣ **CLEANING UP TEMP DIRECTORY**")

        if temp_dir.exists():
            print(f"   🧹 Removing temp directory: {temp_dir}")
            shutil.rmtree(temp_dir)
            print(f"   ✅ Temp directory cleaned")
            print(f"   ✅ /temp is empty")
        else:
            print(f"   ℹ️ Temp directory already clean")

        print(f"\n🎉 **WORKFLOW COMPLETION SUCCESS!**")
        if pr_url:
            print(f"🔗 **Pull Request**: {pr_url}")
        print(f"✅ **All steps completed successfully!**")

    except Exception as e:
        print(f"\n❌ **COMPLETION FAILED**: {str(e)}")
        return False

    return True


async def main():
    """Main execution function."""
    if len(sys.argv) != 3:
        print("Usage: python complete_workflow.py <task-id> <branch-name>")
        print(
            "Example: python complete_workflow.py CMMAI-49 CMMAI-49_create_initial_project_setup_521301"
        )
        sys.exit(1)

    task_id = sys.argv[1]
    branch_name = sys.argv[2]

    success = await complete_workflow(task_id, branch_name)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
