#!/usr/bin/env python3
"""
Workflow Execution CLI

This module provides command-line interface for executing YAML-based workflows
with runtime parameter injection.

Usage:
    python -m workflows execute --workflow standard_dev_workflow --task-id CMMAI-48
    python -m workflows list
    python -m workflows validate --workflow standard_dev_workflow
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Import our core modules
from core.workflow_engine import WorkflowEngine, WorkflowValidationError
from core.plugin_registry import PluginRegistry
from core.config import ConfigManager
from plugins.jira_plugin import JiraPlugin
from plugins.github_plugin import GitHubPlugin
from plugins.slack_plugin import SlackPlugin
from core.plugin_interface import PluginType
from plugins.claude_plugin import ClaudePlugin

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorkflowCLI:
    """Command-line interface for workflow execution"""

    def __init__(self):
        """Initialize the CLI"""
        self.engine: Optional[WorkflowEngine] = None
        self.plugin_registry: Optional[PluginRegistry] = None
        self.config_manager: Optional[ConfigManager] = None
        self.workflows_dir = Path(__file__).parent

    async def initialize(self):
        """Initialize plugins and workflow engine"""
        print("🔧 Initializing workflow execution environment...")

        # Load environment variables
        load_dotenv()

        # Initialize plugin registry
        self.plugin_registry = PluginRegistry()

        # Register plugins with proper configuration
        await self._register_plugins()

        # Initialize workflow engine
        self.engine = WorkflowEngine(plugin_registry=self.plugin_registry)

        print("✅ Workflow execution environment initialized")

    async def _register_plugins(self):
        """Register available plugins with configuration"""
        print("📦 Registering plugins...")

        # Jira Plugin
        if os.getenv("JIRA_API_TOKEN"):
            jira_config = {
                "connection": {
                    "url": os.getenv("JIRA_URL"),
                    "email": os.getenv("JIRA_EMAIL"),
                    "api_token": os.getenv("JIRA_API_TOKEN"),
                },
                "options": {"timeout": 30, "retry_attempts": 3},
            }

            jira_plugin = JiraPlugin(jira_config)
            self.plugin_registry.register_plugin(
                PluginType.TASK_MANAGEMENT, "jira", JiraPlugin
            )

            # Create instance for immediate use
            await jira_plugin.initialize()
            plugin_id = f"{PluginType.TASK_MANAGEMENT.value}.jira"
            self.plugin_registry._instances[plugin_id] = jira_plugin

            print("  ✅ Jira plugin registered")
        else:
            print("  ⚠️ Jira plugin skipped (no JIRA_API_TOKEN)")

        # GitHub Plugin
        if os.getenv("GITHUB_TOKEN"):
            github_config = {
                "connection": {
                    "token": os.getenv("GITHUB_TOKEN"),
                    "api_url": "https://api.github.com",
                },
                "options": {"timeout": 60, "default_branch": "main"},
            }

            github_plugin = GitHubPlugin(github_config)
            self.plugin_registry.register_plugin(
                PluginType.VERSION_CONTROL, "github", GitHubPlugin
            )

            # Create instance for immediate use
            await github_plugin.initialize()
            plugin_id = f"{PluginType.VERSION_CONTROL.value}.github"
            self.plugin_registry._instances[plugin_id] = github_plugin

            print("  ✅ GitHub plugin registered")
        else:
            print("  ⚠️ GitHub plugin skipped (no GITHUB_TOKEN)")

        # Slack Plugin
        if os.getenv("SLACK_BOT_TOKEN"):
            slack_config = {
                "connection": {
                    "token": os.getenv("SLACK_BOT_TOKEN"),
                    "api_url": "https://slack.com/api",
                },
                "options": {"default_channel": "#development", "timeout": 30},
            }

            slack_plugin = SlackPlugin(slack_config)
            self.plugin_registry.register_plugin(
                PluginType.COMMUNICATION, "slack", SlackPlugin
            )

            # Create instance for immediate use
            await slack_plugin.initialize()
            plugin_id = f"{PluginType.COMMUNICATION.value}.slack"
            self.plugin_registry._instances[plugin_id] = slack_plugin

            print("  ✅ Slack plugin registered")
        else:
            print("  ⚠️ Slack plugin skipped (no SLACK_BOT_TOKEN)")

        # Claude AI Plugin
        if os.getenv("ANTHROPIC_API_KEY"):
            claude_config = {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4000,
                "temperature": 0.3
            }

            claude_plugin = ClaudePlugin(claude_config)
            self.plugin_registry.register_plugin(
                PluginType.AI_PROVIDER, "claude", ClaudePlugin
            )

            # Create instance for immediate use
            await claude_plugin.initialize()
            plugin_id = f"{PluginType.AI_PROVIDER.value}.claude"
            self.plugin_registry._instances[plugin_id] = claude_plugin

            print("  ✅ Claude AI plugin registered")
        else:
            print("  ⚠️ Claude AI plugin skipped (no ANTHROPIC_API_KEY)")

    def list_workflows(self) -> List[str]:
        """List available workflow files"""
        workflows = []

        for yaml_file in self.workflows_dir.glob("*.yaml"):
            if not yaml_file.name.startswith("_"):  # Skip private workflows
                workflows.append(yaml_file.stem)

        return sorted(workflows)

    def get_workflow_path(self, workflow_name: str) -> Optional[Path]:
        """Get path to workflow YAML file"""
        workflow_path = self.workflows_dir / f"{workflow_name}.yaml"

        if workflow_path.exists():
            return workflow_path
        return None

    async def validate_workflow(self, workflow_name: str) -> bool:
        """Validate a workflow file"""
        workflow_path = self.get_workflow_path(workflow_name)

        if not workflow_path:
            print(f"❌ Workflow '{workflow_name}' not found")
            return False

        try:
            # Load and parse workflow
            workflow = self.engine.load_workflow_from_file(str(workflow_path))
            print(f"📋 Loaded workflow: {workflow.name}")

            # Validate workflow
            validation = self.engine.validate_workflow(workflow)

            if validation.is_valid:
                print("✅ Workflow validation passed")

                if validation.warnings:
                    print("⚠️ Warnings:")
                    for warning in validation.warnings:
                        print(f"  - {warning}")

                return True
            else:
                print("❌ Workflow validation failed")
                print("Errors:")
                for error in validation.errors:
                    print(f"  - {error}")

                if validation.warnings:
                    print("Warnings:")
                    for warning in validation.warnings:
                        print(f"  - {warning}")

                return False

        except WorkflowValidationError as e:
            print(f"❌ Workflow parsing failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error validating workflow: {e}")
            return False

    async def execute_workflow(
        self, workflow_name: str, runtime_params: Dict[str, Any]
    ) -> bool:
        """Execute a workflow with runtime parameters"""

        workflow_path = self.get_workflow_path(workflow_name)
        if not workflow_path:
            print(f"❌ Workflow '{workflow_name}' not found")
            return False

        try:
            # Load workflow
            workflow = self.engine.load_workflow_from_file(str(workflow_path))
            print(f"🚀 Executing workflow: {workflow.name}")

            # Validate workflow first
            validation = self.engine.validate_workflow(workflow)
            if not validation.is_valid:
                print("❌ Workflow validation failed, cannot execute:")
                for error in validation.errors:
                    print(f"  - {error}")
                return False

            # Execute workflow with runtime parameters
            result = await self.engine.execute_workflow(workflow, runtime_params)

            # Report results
            if result.success:
                print(f"✅ Workflow completed successfully!")
                print(f"⏱️ Execution time: {result.execution_time}")
                print(
                    f"📊 Steps completed: {len([s for s in result.step_results if s.success])}/{len(result.step_results)}"
                )

                if result.total_cost > 0:
                    print(f"💰 Total cost: ${result.total_cost:.2f}")

                return True
            else:
                print(f"❌ Workflow failed: {result.error_message}")
                print(f"⏱️ Execution time: {result.execution_time}")
                print("Step results:")

                for step_result in result.step_results:
                    status = "✅" if step_result.success else "❌"
                    print(f"  {status} {step_result.step_name}: {step_result.duration}")
                    if step_result.error_message:
                        print(f"     Error: {step_result.error_message}")

                return False

        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def cleanup(self):
        """Cleanup resources"""
        if self.plugin_registry:
            await self.plugin_registry.cleanup_all_plugins()


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Execute YAML-based workflows with AI-powered automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute workflow with parameters
  python -m workflows execute --workflow standard_dev_workflow --task-id CMMAI-48 --repository-url git@github.com:user/repo.git

  # List available workflows
  python -m workflows list
  
  # Validate workflow  
  python -m workflows validate --workflow standard_dev_workflow
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute a workflow")
    execute_parser.add_argument(
        "--workflow", required=True, help="Workflow name (without .yaml extension)"
    )
    execute_parser.add_argument(
        "--task-id", help="Task ID for task management workflows"
    )
    execute_parser.add_argument(
        "--repository-url", help="Repository URL for version control workflows"
    )
    execute_parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for version control operations",
    )
    execute_parser.add_argument(
        "--notify-team", action="store_true", help="Enable team notifications"
    )
    execute_parser.add_argument(
        "--team-channel", default="#development", help="Team channel for notifications"
    )
    execute_parser.add_argument(
        "--agent-id", default="ai-dev-agent-001", help="Agent identifier for tracking"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List available workflows")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a workflow")
    validate_parser.add_argument(
        "--workflow", required=True, help="Workflow name to validate"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cli = WorkflowCLI()

    try:
        if args.command == "list":
            print("📋 Available workflows:")
            workflows = cli.list_workflows()

            if not workflows:
                print("  No workflows found")
                return 0

            for workflow in workflows:
                print(f"  - {workflow}")
            return 0

        # For execute and validate, we need to initialize
        await cli.initialize()

        if args.command == "validate":
            success = await cli.validate_workflow(args.workflow)
            return 0 if success else 1

        elif args.command == "execute":
            # Build runtime parameters from CLI arguments
            runtime_params = {}

            if args.task_id:
                runtime_params["task_id"] = args.task_id
            if args.repository_url:
                runtime_params["repository_url"] = args.repository_url
            if args.base_branch:
                runtime_params["base_branch"] = args.base_branch
            if args.agent_id:
                runtime_params["agent_id"] = args.agent_id
            if args.team_channel:
                runtime_params["team_channel"] = args.team_channel

            runtime_params["notify_team"] = args.notify_team

            print(f"🔧 Runtime parameters: {runtime_params}")

            success = await cli.execute_workflow(args.workflow, runtime_params)
            return 0 if success else 1

    except KeyboardInterrupt:
        print("\\n⚠️ Execution interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
