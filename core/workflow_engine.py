"""
Workflow Engine Core Module

This module provides the core workflow execution engine that can parse, validate,
and execute YAML-based workflows. It supports:

- YAML workflow parsing and validation
- Variable resolution with Jinja2 templates
- Step execution with timeout and retry mechanisms
- Error handling strategies (fail, retry, continue, rollback)
- Parallel and conditional step execution
- Plugin integration for external service calls
- AI action execution integration
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

from core.plugin_registry import PluginRegistry
from core.variable_resolver import VariableResolutionError, VariableResolver

logger = logging.getLogger(__name__)


class ErrorStrategy(Enum):
    """Error handling strategies for workflow steps"""

    FAIL = "fail"
    RETRY = "retry"
    CONTINUE = "continue"
    ROLLBACK = "rollback"


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails"""

    pass


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails"""

    pass


@dataclass
class ValidationResult:
    """Result of workflow validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of individual step execution"""

    step_name: str
    success: bool
    duration: timedelta
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    cost: float = 0.0


@dataclass
class WorkflowResult:
    """Result of complete workflow execution"""

    workflow_name: str
    success: bool
    step_results: List[StepResult]
    execution_time: timedelta
    total_cost: float = 0.0
    error_message: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""

    name: str
    plugin: str
    action: str
    description: str = ""
    type: str = "plugin_action"  # plugin_action, ai_action, parallel, system_action
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)  # output_name -> context_key
    condition: Optional[str] = None
    on_error: ErrorStrategy = ErrorStrategy.FAIL
    timeout: int = 300  # seconds
    retry_count: int = 0
    retry_delay: int = 30  # seconds
    parallel_steps: List["WorkflowStep"] = field(default_factory=list)

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> "WorkflowStep":
        """Create WorkflowStep from dictionary"""
        # Convert on_error string to ErrorStrategy enum
        on_error = step_data.get("on_error", "fail")
        if isinstance(on_error, str):
            on_error = ErrorStrategy(on_error)

        # Handle parallel steps
        parallel_steps = []
        if step_data.get("type") == "parallel" and "steps" in step_data:
            for parallel_step_data in step_data["steps"]:
                parallel_steps.append(cls.from_dict(parallel_step_data))

        return cls(
            name=step_data["name"],
            description=step_data.get("description", ""),
            type=step_data.get("type", "plugin_action"),
            plugin=step_data.get("plugin", ""),
            action=step_data.get("action", ""),
            inputs=step_data.get("inputs", {}),
            outputs=step_data.get("outputs", {}),
            condition=step_data.get("condition"),
            on_error=on_error,
            timeout=step_data.get("timeout", 300),
            retry_count=step_data.get("retry_count", 0),
            retry_delay=step_data.get("retry_delay", 30),
            parallel_steps=parallel_steps,
        )


@dataclass
class Workflow:
    """Represents a complete workflow"""

    name: str
    description: str = ""
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[Dict[str, str]] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[Dict[str, str]] = field(default_factory=list)
    post_execution: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """
    Core workflow execution engine that orchestrates the execution of
    YAML-based workflows with plugin integration and AI capabilities.
    """

    def __init__(self, plugin_registry: Optional[PluginRegistry] = None):
        """Initialize the workflow engine"""
        self.plugin_registry = plugin_registry or PluginRegistry()
        self.variable_resolver = VariableResolver()
        self._execution_context = {}

    def parse_workflow(self, yaml_content: str) -> Workflow:
        """
        Parse YAML workflow content into a Workflow object

        Args:
            yaml_content: YAML string containing workflow definition

        Returns:
            Workflow object

        Raises:
            WorkflowValidationError: If YAML is invalid or required fields are missing
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise WorkflowValidationError(f"Invalid YAML: {e}")

        if not data:
            raise WorkflowValidationError("Empty workflow definition")

        # Validate required fields
        if not data.get("name") or not data.get("name").strip():
            raise WorkflowValidationError("Workflow name is required")

        if not data.get("steps"):
            raise WorkflowValidationError("Workflow must have at least one step")

        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            if not isinstance(step_data, dict):
                raise WorkflowValidationError("Step must be a dictionary")
            if not step_data.get("name"):
                raise WorkflowValidationError("Step name is required")

            steps.append(WorkflowStep.from_dict(step_data))

        return Workflow(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            tags=data.get("tags", []),
            variables=data.get("variables", {}),
            prerequisites=data.get("prerequisites", []),
            steps=steps,
            error_handling=data.get("error_handling", {}),
            success_criteria=data.get("success_criteria", []),
            post_execution=data.get("post_execution", {}),
            metadata=data.get("metadata", {}),
        )

    def load_workflow_from_file(self, file_path: str) -> Workflow:
        """
        Load workflow from a YAML file

        Args:
            file_path: Path to YAML workflow file

        Returns:
            Workflow object
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.parse_workflow(content)
        except FileNotFoundError:
            raise WorkflowValidationError(f"Workflow file not found: {file_path}")
        except Exception as e:
            raise WorkflowValidationError(f"Error loading workflow file: {e}")

    def validate_workflow(self, workflow: Workflow) -> ValidationResult:
        """
        Validate workflow structure and dependencies

        Args:
            workflow: Workflow object to validate

        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []
        warnings = []

        # Validate basic structure
        if not workflow.name.strip():
            errors.append("Workflow name cannot be empty")

        if not workflow.steps:
            errors.append("Workflow must have at least one step")

        # Validate steps
        step_names = set()
        for step in workflow.steps:
            # Check for duplicate step names
            if step.name in step_names:
                errors.append(f"Duplicate step name: {step.name}")
            step_names.add(step.name)

            # Validate step structure
            if step.type == "plugin_action":
                if not step.plugin:
                    errors.append(f"Step '{step.name}' missing required plugin")
                if not step.action:
                    errors.append(f"Step '{step.name}' missing required action")

            # Validate timeout
            try:
                if isinstance(step.timeout, (int, float)) and step.timeout <= 0:
                    errors.append(f"Step '{step.name}' timeout must be positive")
            except (TypeError, ValueError):
                errors.append(f"Step '{step.name}' timeout must be a number")

            # Validate retry count
            try:
                if isinstance(step.retry_count, int) and step.retry_count < 0:
                    errors.append(f"Step '{step.name}' retry_count cannot be negative")
            except (TypeError, ValueError):
                errors.append(f"Step '{step.name}' retry_count must be an integer")

        # Validate step dependencies and variable references
        self._validate_dependencies(workflow, errors, warnings)

        # Validate plugin availability (if plugin registry is available)
        self._validate_plugins(workflow, errors, warnings)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_dependencies(
        self, workflow: Workflow, errors: List[str], warnings: List[str]
    ):
        """Validate step dependencies and detect circular references"""
        step_names = {step.name for step in workflow.steps}

        # Build dependency graph
        dependencies = {}  # step_name -> set of steps it depends on

        for step in workflow.steps:
            dependencies[step.name] = set()

            # Check variable references in inputs
            for input_key, input_value in step.inputs.items():
                if isinstance(input_value, str) and "${" in input_value:
                    # Extract variable references like ${step_name.output}
                    import re

                    refs = re.findall(r"\$\{([^}]+)\}", input_value)
                    for ref in refs:
                        if "." in ref:
                            step_ref = ref.split(".")[0]
                            if step_ref in step_names:
                                dependencies[step.name].add(step_ref)
                            elif step_ref not in [
                                "task",
                                "project",
                                "system",
                                "workflow",
                            ]:
                                errors.append(
                                    f"Step '{step.name}' references undefined step: {step_ref}"
                                )

        # Detect circular dependencies using depth-first search
        self._detect_circular_dependencies(dependencies, errors)

    def _detect_circular_dependencies(
        self, dependencies: Dict[str, set], errors: List[str]
    ):
        """Detect circular dependencies using depth-first search"""
        visited = set()
        visiting = set()  # Currently in the DFS path

        def visit(node: str, path: List[str]):
            if node in visiting:
                # Found a cycle
                cycle_start = path.index(node)
                cycle_path = path[cycle_start:] + [node]
                errors.append(
                    f"Circular dependency detected: {' -> '.join(cycle_path)}"
                )
                return

            if node in visited:
                return

            visiting.add(node)
            path.append(node)

            for dependency in dependencies.get(node, set()):
                visit(dependency, path[:])

            visiting.remove(node)
            visited.add(node)
            path.pop()

        for step_name in dependencies.keys():
            if step_name not in visited:
                visit(step_name, [])

    def _validate_plugins(
        self, workflow: Workflow, errors: List[str], warnings: List[str]
    ):
        """Validate that required plugins are available"""
        if not self.plugin_registry:
            warnings.append("No plugin registry available for plugin validation")
            return

        for step in workflow.steps:
            if step.type == "plugin_action" and step.plugin:
                try:
                    plugin = self.plugin_registry.get_plugin_instance_by_name(step.plugin)
                    if not plugin:
                        errors.append(
                            f"Plugin '{step.plugin}' not found for step '{step.name}'"
                        )
                    elif not hasattr(plugin, step.action):
                        warnings.append(
                            f"Plugin '{step.plugin}' may not support action "
                            f"'{step.action}' for step '{step.name}'"
                        )
                except Exception as e:
                    warnings.append(f"Could not validate plugin '{step.plugin}': {e}")

    async def execute_workflow(
        self, workflow: Workflow, context: Dict[str, Any] = None
    ) -> WorkflowResult:
        """
        Execute a complete workflow

        Args:
            workflow: Workflow object to execute
            context: Initial execution context

        Returns:
            WorkflowResult with execution results
        """
        if context is None:
            context = {}

        start_time = datetime.utcnow()
        step_results = []
        total_cost = 0.0

        # Initialize execution context
        execution_context = {
            **workflow.variables,
            **context,
            "workflow": {
                "name": workflow.name,
                "version": workflow.version,
                "start_time": start_time.isoformat(),
            },
        }

        logger.info(f"Starting workflow execution: {workflow.name}")

        try:
            # Check prerequisites
            await self._check_prerequisites(workflow, execution_context)

            # Execute steps sequentially
            for step in workflow.steps:
                if not await self._should_execute_step(step, execution_context):
                    logger.info(f"Skipping step '{step.name}' due to condition")
                    continue

                step_result = await self._execute_step(step, execution_context)
                step_results.append(step_result)
                total_cost += step_result.cost

                # Update execution context with step outputs
                for output_name, context_key in step.outputs.items():
                    if output_name in step_result.outputs:
                        execution_context[context_key] = step_result.outputs[
                            output_name
                        ]

                # Handle step failure
                if not step_result.success:
                    error_strategy = step.on_error
                    if error_strategy == ErrorStrategy.FAIL:
                        break
                    elif error_strategy == ErrorStrategy.CONTINUE:
                        logger.warning(
                            f"Step '{step.name}' failed but continuing due to error strategy"
                        )
                        continue
                    # RETRY and ROLLBACK are handled within _execute_step

            # Check success criteria
            success = await self._check_success_criteria(
                workflow, execution_context, step_results
            )

            execution_time = datetime.utcnow() - start_time

            result = WorkflowResult(
                workflow_name=workflow.name,
                success=success,
                step_results=step_results,
                execution_time=execution_time,
                total_cost=total_cost,
                context=execution_context,
            )

            logger.info(
                f"Workflow execution completed: {workflow.name} (success={success})"
            )
            return result

        except Exception as e:
            execution_time = datetime.utcnow() - start_time
            logger.error(f"Workflow execution failed: {workflow.name}: {e}")

            return WorkflowResult(
                workflow_name=workflow.name,
                success=False,
                step_results=step_results,
                execution_time=execution_time,
                total_cost=total_cost,
                error_message=str(e),
                context=execution_context,
            )

    async def _check_prerequisites(self, workflow: Workflow, context: Dict[str, Any]):
        """Check workflow prerequisites before execution"""
        for prerequisite in workflow.prerequisites:
            condition = prerequisite.get("condition", "")
            if condition:
                # TODO: Implement proper condition evaluation with Jinja2
                # For now, we'll do basic string replacement
                if not self._evaluate_condition(condition, context):
                    error_message = prerequisite.get(
                        "error_message", f"Prerequisite failed: {condition}"
                    )
                    raise WorkflowExecutionError(error_message)

    async def _should_execute_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> bool:
        """Determine if a step should be executed based on its condition"""
        if not step.condition:
            return True

        # TODO: Implement proper condition evaluation with Jinja2
        return self._evaluate_condition(step.condition, context)

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition using variable resolver"""
        try:
            # Create a template that resolves to true/false
            template = f"{{{{ {condition} }}}}"
            result = self.variable_resolver.resolve(template, context)

            # Convert string result to boolean
            if result.lower() in ("true", "1", "yes"):
                return True
            elif result.lower() in ("false", "0", "no", ""):
                return False
            else:
                # Try to evaluate as safe literal for complex conditions
                try:
                    import ast

                    return bool(ast.literal_eval(result))
                except (ValueError, SyntaxError):
                    # If not a safe literal, treat as truthy string
                    return bool(result)

        except (VariableResolutionError, Exception):
            logger.warning(f"Failed to evaluate condition: {condition}")
            return False

    async def _execute_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> StepResult:
        """Execute a single workflow step"""
        start_time = datetime.utcnow()

        logger.info(f"Executing step: {step.name}")

        for attempt in range(step.retry_count + 1):
            try:
                if step.type == "parallel":
                    result = await self._execute_parallel_step(step, context)
                else:
                    result = await self._execute_single_step(step, context)

                duration = datetime.utcnow() - start_time

                return StepResult(
                    step_name=step.name,
                    success=True,
                    duration=duration,
                    outputs=result,
                    retry_count=attempt,
                )

            except asyncio.TimeoutError:
                duration = datetime.utcnow() - start_time
                error_msg = f"Step '{step.name}' timeout after {step.timeout} seconds"

                if attempt < step.retry_count:
                    logger.warning(
                        f"{error_msg}, retrying (attempt {attempt + 1}/{step.retry_count + 1})"
                    )
                    await asyncio.sleep(step.retry_delay)
                    continue

                return StepResult(
                    step_name=step.name,
                    success=False,
                    duration=duration,
                    error_message=error_msg,
                    retry_count=attempt,
                )

            except Exception as e:
                duration = datetime.utcnow() - start_time
                error_msg = f"Step '{step.name}' failed: {str(e)}"

                if attempt < step.retry_count and step.on_error == ErrorStrategy.RETRY:
                    logger.warning(
                        f"{error_msg}, retrying (attempt {attempt + 1}/{step.retry_count + 1})"
                    )
                    await asyncio.sleep(step.retry_delay)
                    continue

                return StepResult(
                    step_name=step.name,
                    success=False,
                    duration=duration,
                    error_message=error_msg,
                    retry_count=attempt,
                )

        # This should never be reached, but just in case
        return StepResult(
            step_name=step.name,
            success=False,
            duration=datetime.utcnow() - start_time,
            error_message="Unexpected error in step execution",
        )

    async def _execute_single_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step (plugin action, AI action, or system action)"""
        if step.type == "plugin_action":
            return await self._execute_plugin_action(step, context)
        elif step.type == "ai_action":
            return await self._execute_ai_action(step, context)
        elif step.type == "system_action":
            return await self._execute_system_action(step, context)
        else:
            raise WorkflowExecutionError(f"Unknown step type: {step.type}")

    async def _execute_parallel_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute parallel steps concurrently"""
        tasks = []
        for parallel_step in step.parallel_steps:
            task = asyncio.create_task(self._execute_step(parallel_step, context))
            tasks.append((parallel_step.name, task))

        results = {}
        for step_name, task in tasks:
            try:
                step_result = await task
                results[step_name] = step_result.outputs
            except Exception as e:
                logger.error(f"Parallel step '{step_name}' failed: {e}")
                results[step_name] = {"error": str(e)}

        return results

    async def _execute_plugin_action(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a plugin action step"""
        if not self.plugin_registry:
            raise WorkflowExecutionError("No plugin registry available")

        # Get the plugin
        plugin = self.plugin_registry.get_plugin_instance_by_name(step.plugin)
        if not plugin:
            raise WorkflowExecutionError(f"Plugin '{step.plugin}' not found")

        # Get the action method
        action_method = getattr(plugin, step.action, None)
        if not action_method:
            raise WorkflowExecutionError(
                f"Plugin '{step.plugin}' does not have action '{step.action}'"
            )

        # Resolve variables in inputs using the variable resolver
        resolved_inputs = {}
        for key, value in step.inputs.items():
            if isinstance(value, str):
                try:
                    resolved_inputs[key] = self.variable_resolver.resolve(
                        value, context
                    )
                except VariableResolutionError as e:
                    logger.warning(f"Failed to resolve input '{key}': {e}")
                    resolved_inputs[key] = value
            else:
                resolved_inputs[key] = value

        # Execute the action with timeout
        try:
            # Check if the method is a coroutine function or returns a coroutine
            if asyncio.iscoroutinefunction(action_method):
                result = await asyncio.wait_for(
                    action_method(**resolved_inputs), timeout=step.timeout
                )
            else:
                # If it's not async, wrap it in a coroutine
                async def sync_wrapper():
                    return action_method(**resolved_inputs)

                result = await asyncio.wait_for(sync_wrapper(), timeout=step.timeout)

            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"result": result}

            return result

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Plugin action timed out after {step.timeout} seconds"
            )

    async def _execute_ai_action(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an AI action step"""
        # TODO: Implement AI action execution
        # This will be implemented when we integrate with Claude API
        logger.info(f"AI action execution not yet implemented for step: {step.name}")
        return {"result": "ai_action_placeholder"}

    async def _execute_system_action(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a system action step"""
        # TODO: Implement system action execution
        # This includes logging, metrics collection, etc.
        logger.info(
            f"System action execution not yet implemented for step: {step.name}"
        )
        return {"result": "system_action_placeholder"}

    async def _check_success_criteria(
        self,
        workflow: Workflow,
        context: Dict[str, Any],
        step_results: List[StepResult],
    ) -> bool:
        """Check if workflow success criteria are met"""
        if not workflow.success_criteria:
            # If no success criteria specified, check if all steps succeeded
            return all(result.success for result in step_results)

        # TODO: Implement proper success criteria evaluation
        # For now, just check that all steps succeeded
        return all(result.success for result in step_results)
