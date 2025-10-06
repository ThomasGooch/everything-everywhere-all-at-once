#!/usr/bin/env python3
"""
Main CLI entry point for AI Development Automation System.
Usage: python main.py --workflows <workflow_name> <args...>
"""

import argparse
import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List


class WorkflowRunner:
    """Discovers and executes workflows from the /workflows directory."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.workflows_dir = self.project_root / "workflows"
        
    def discover_workflows(self) -> Dict[str, Path]:
        """Discover all available workflows in the workflows directory."""
        workflows = {}
        
        if not self.workflows_dir.exists():
            return workflows
            
        for workflow_file in self.workflows_dir.glob("*.py"):
            # Skip __init__.py and __main__.py
            if workflow_file.stem.startswith("__"):
                continue
                
            workflows[workflow_file.stem] = workflow_file
            
        return workflows
    
    def load_workflow(self, workflow_name: str) -> Any:
        """Dynamically load a workflow module."""
        workflows = self.discover_workflows()
        
        if workflow_name not in workflows:
            available = ", ".join(workflows.keys())
            raise ValueError(f"Workflow '{workflow_name}' not found. Available workflows: {available}")
            
        workflow_path = workflows[workflow_name]
        
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(workflow_name, workflow_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load workflow module from {workflow_path}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[workflow_name] = module
        spec.loader.exec_module(module)
        
        return module
    
    async def execute_workflow(self, workflow_name: str, args: List[str]) -> Dict[str, Any]:
        """Execute the specified workflow with given arguments."""
        try:
            # Load the workflow module
            workflow_module = self.load_workflow(workflow_name)
            
            # Look for a main function or workflow class
            if hasattr(workflow_module, 'main'):
                # If it has a main function, call it with args
                if asyncio.iscoroutinefunction(workflow_module.main):
                    return await workflow_module.main(args)
                else:
                    return workflow_module.main(args)
                    
            elif hasattr(workflow_module, 'WorkflowExecutor'):
                # If it has a WorkflowExecutor class, instantiate and run it
                executor = workflow_module.WorkflowExecutor(*args)
                if hasattr(executor, 'run') and asyncio.iscoroutinefunction(executor.run):
                    return await executor.run()
                elif hasattr(executor, 'run'):
                    return executor.run()
                else:
                    raise AttributeError(f"WorkflowExecutor in {workflow_name} must have a 'run' method")
                    
            else:
                raise AttributeError(f"Workflow {workflow_name} must have either a 'main' function or 'WorkflowExecutor' class")
                
        except Exception as e:
            logging.error(f"Failed to execute workflow '{workflow_name}': {e}")
            return {"success": False, "error": str(e)}


async def async_main():
    """Async main function for the CLI."""
    parser = argparse.ArgumentParser(
        description="AI Development Automation System",
        epilog="Example: python main.py --workflows real_development_workflow TASK-123"
    )
    
    parser.add_argument(
        "--workflows",
        metavar=("WORKFLOW_NAME", "ARGS"),
        nargs="+",
        help="Execute a workflow with arguments"
    )
    
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List all available workflows"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    runner = WorkflowRunner()
    
    try:
        if args.list_workflows:
            workflows = runner.discover_workflows()
            if workflows:
                print("Available workflows:")
                for name in sorted(workflows.keys()):
                    print(f"  • {name}")
            else:
                print("No workflows found in /workflows directory")
            return {"success": True}
            
        if args.workflows:
            workflow_name = args.workflows[0]
            workflow_args = args.workflows[1:]
            
            logger.info(f"Executing workflow: {workflow_name} with args: {workflow_args}")
            result = await runner.execute_workflow(workflow_name, workflow_args)
            
            if result.get("success", False):
                print("✅ Workflow completed successfully")
                logger.info(f"Workflow '{workflow_name}' completed successfully")
            else:
                print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
                logger.error(f"Workflow '{workflow_name}' failed")
                sys.exit(1)
                
            return result
            
        else:
            parser.print_help()
            return {"success": True}
            
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
        print("\n🛑 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"System execution failed: {e}")
        print(f"❌ System error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Sync entry point that runs async main."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()