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
                    plugin = self.plugin_registry.get_plugin_instance_by_name(
                        step.plugin
                    )
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

                # Extract cost from result if available
                cost = result.get("cost", 0.0) if isinstance(result, dict) else 0.0
                
                return StepResult(
                    step_name=step.name,
                    success=True,
                    duration=duration,
                    outputs=result,
                    retry_count=attempt,
                    cost=cost,
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
        """Execute an AI action step using Claude API"""
        try:
            # Get the Claude plugin instance
            claude_plugin = self.plugin_registry.get_plugin_instance_by_name("claude")
            if not claude_plugin:
                raise WorkflowExecutionError(
                    "Claude AI plugin not available for AI actions"
                )

            # Resolve step inputs with context
            resolved_inputs = self._resolve_step_inputs(step.inputs, context)

            # Extract common AI parameters
            max_tokens = resolved_inputs.get(
                "max_tokens", step.max_tokens if hasattr(step, "max_tokens") else 2000
            )
            temperature = resolved_inputs.get(
                "temperature", step.temperature if hasattr(step, "temperature") else 0.3
            )

            # Build the prompt based on the step configuration
            prompt = await self._build_ai_prompt(step, resolved_inputs, context)

            logger.info(f"Executing AI action '{step.name}' with Claude")

            # Generate response using Claude
            result = await claude_plugin.generate_text(
                prompt=prompt, max_tokens=max_tokens, temperature=temperature
            )

            if not result.success:
                raise WorkflowExecutionError(
                    f"Claude AI generation failed: {result.error}"
                )

            # Structure the response according to expected outputs
            ai_response = {
                "generated_text": result.data["generated_text"],
                "model": result.data["model"],
                "input_tokens": result.data["input_tokens"],
                "output_tokens": result.data["output_tokens"],
                "cost": result.data["cost"],
            }

            # If step specifies specific output structure, try to parse it
            if step.name in [
                "analyze_codebase",
                "generate_implementation_plan",
                "generate_code_implementation",
            ]:
                ai_response = await self._parse_structured_ai_response(
                    step.name, result.data["generated_text"], ai_response
                )

            logger.info(
                f"AI action '{step.name}' completed successfully (cost: ${result.data['cost']:.4f})"
            )

            return ai_response

        except Exception as e:
            logger.error(f"Error executing AI action '{step.name}': {e}")
            raise WorkflowExecutionError(f"AI action failed: {e}")

    async def _build_ai_prompt(
        self,
        step: WorkflowStep,
        resolved_inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """Build AI prompt based on step configuration and context"""

        # Check if step has a prompt_template specified
        if hasattr(step, "prompt_template") and step.prompt_template:
            # TODO: Load template from file and render with inputs
            # For now, use a simple template based on step name
            pass

        # Build prompt based on step name and inputs
        if step.name == "analyze_codebase":
            return self._build_codebase_analysis_prompt(resolved_inputs)
        elif step.name == "generate_implementation_plan":
            return self._build_implementation_plan_prompt(resolved_inputs)
        elif step.name == "generate_code_implementation":
            return self._build_code_generation_prompt(resolved_inputs)
        elif step.name == "generate_documentation":
            return self._build_documentation_prompt(resolved_inputs)
        else:
            # Generic AI prompt
            task = resolved_inputs.get("task", {})
            
            # Handle case where task might be a string instead of dict
            if isinstance(task, str):
                task_title = task
                task_description = task
            else:
                task_title = task.get('title', 'No title provided') if isinstance(task, dict) else str(task)
                task_description = task.get('description', 'No description provided') if isinstance(task, dict) else str(task)
            
            prompt_parts = [
                f"Task: {task_title}",
                f"Description: {task_description}",
                "",
                "Please provide a detailed response for this development task.",
            ]
            return "\n".join(prompt_parts)

    def _build_codebase_analysis_prompt(self, inputs: Dict[str, Any]) -> str:
        """Build prompt for codebase analysis"""
        task = inputs.get("task", {})
        repository_path = inputs.get("repository_path", "")

        # Handle case where task might be a string instead of dict
        if isinstance(task, str):
            task_title = task
            task_description = task
        else:
            task_title = task.get('title', 'No title') if isinstance(task, dict) else str(task)
            task_description = task.get('description', 'No description') if isinstance(task, dict) else str(task)

        return f"""Analyze the codebase for the following development task:

Task: {task_title}
Description: {task_description}
Repository Path: {repository_path}

Please provide a comprehensive analysis including:
1. Codebase structure and architecture
2. Relevant files and modules for this task
3. Existing patterns and conventions
4. Dependencies and frameworks used
5. Potential integration points
6. Any constraints or considerations

Format your response as a structured analysis that can guide implementation planning."""

    def _build_implementation_plan_prompt(self, inputs: Dict[str, Any]) -> str:
        """Build prompt for implementation plan generation"""
        task = inputs.get("task", {})
        codebase_analysis = inputs.get("codebase_analysis", {})

        # Handle case where inputs might be strings instead of dicts
        if isinstance(task, str):
            task_title = task
            task_description = task
        else:
            task_title = task.get('title', 'No title') if isinstance(task, dict) else str(task)
            task_description = task.get('description', 'No description') if isinstance(task, dict) else str(task)
            
        analysis_text = (
            codebase_analysis.get('generated_text', 'No analysis available') 
            if isinstance(codebase_analysis, dict) 
            else str(codebase_analysis)
        )

        return f"""Create a detailed implementation plan for the following task:

Task: {task_title}
Description: {task_description}

Codebase Analysis:
{analysis_text}

Please provide an implementation plan including:
1. Summary of the approach
2. Files to be modified or created
3. Key changes required
4. Implementation steps in order
5. Testing strategy
6. Estimated effort and complexity
7. Potential risks and mitigation strategies

Format the response as a structured plan that can guide code generation."""

    def _build_code_generation_prompt(self, inputs: Dict[str, Any]) -> str:
        """Build prompt for code generation"""
        task = inputs.get("task", {})
        plan = inputs.get("plan", {})
        codebase_analysis = inputs.get("codebase_analysis", {})

        # Handle case where inputs might be strings instead of dicts
        if isinstance(task, str):
            task_title = task
            task_description = task
        else:
            task_title = task.get('title', 'No title') if isinstance(task, dict) else str(task)
            task_description = task.get('description', 'No description') if isinstance(task, dict) else str(task)
            
        plan_text = (
            plan.get('generated_text', 'No plan available') 
            if isinstance(plan, dict) 
            else str(plan)
        )
        
        analysis_text = (
            codebase_analysis.get('generated_text', 'No context available') 
            if isinstance(codebase_analysis, dict) 
            else str(codebase_analysis)
        )

        return f"""Generate production-ready code implementation for:

Task: {task_title}
Description: {task_description}

Implementation Plan:
{plan_text}

Codebase Context:
{analysis_text}

Requirements:
- Write clean, maintainable code
- Follow existing code patterns and conventions
- Include proper error handling
- Add comprehensive docstrings and comments
- Include unit tests
- Follow security best practices

Please provide:
1. Complete code files with full implementation
2. Unit test files
3. Any configuration or migration files needed
4. Clear file paths and organization
5. Installation/setup instructions if needed

Format your response with clear file separations and explanations."""

    def _build_documentation_prompt(self, inputs: Dict[str, Any]) -> str:
        """Build prompt for documentation generation"""
        task = inputs.get("task", {})
        implementation = inputs.get("implementation", {})

        # Handle case where inputs might be strings instead of dicts
        if isinstance(task, str):
            task_title = task
            task_description = task
        else:
            task_title = task.get('title', 'No title') if isinstance(task, dict) else str(task)
            task_description = task.get('description', 'No description') if isinstance(task, dict) else str(task)
            
        implementation_text = (
            implementation.get('generated_text', 'No implementation details available') 
            if isinstance(implementation, dict) 
            else str(implementation)
        )

        return f"""Generate comprehensive documentation for the implementation of:

Task: {task_title}
Description: {task_description}

Implementation:
{implementation_text}

Please create:
1. API documentation (if applicable)
2. Usage examples and tutorials
3. Configuration guide
4. Architecture overview
5. Troubleshooting guide

Format as clear, well-structured documentation suitable for developers."""

    async def _parse_structured_ai_response(
        self, step_name: str, generated_text: str, base_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI response into structured format based on step type"""

        # For now, return the base response with the generated text
        # In a more advanced implementation, we could parse the text
        # into structured data based on the step requirements

        if step_name == "analyze_codebase":
            base_response.update(
                {
                    "analysis": generated_text,
                    "structure": "analyzed",
                    "patterns": "identified",
                }
            )
        elif step_name == "generate_implementation_plan":
            base_response.update(
                {
                    "plan": generated_text,
                    "files_to_modify": ["to_be_parsed"],
                    "estimated_effort": "medium",
                    "summary": generated_text[:200] + "..."
                    if len(generated_text) > 200
                    else generated_text,
                }
            )
        elif step_name == "generate_code_implementation":
            base_response.update(
                {
                    "implementation": generated_text,
                    "files": ["to_be_parsed"],
                    "tests": ["to_be_parsed"],
                    "stats": {"lines_added": 0, "lines_removed": 0},
                }
            )

        return base_response

    def _resolve_step_inputs(
        self, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve step inputs with proper handling of complex data structures"""
        resolved_inputs = {}

        for key, value in inputs.items():
            if isinstance(value, str) and "${" in value:
                # Try to get the actual context object if it's a reference first
                if value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    if var_name in context:
                        resolved_inputs[key] = context[var_name]
                    else:
                        # Fallback to variable resolver if context key doesn't exist
                        resolved_inputs[key] = self.variable_resolver.resolve(value, context)
                else:
                    # This is a template string that needs resolution
                    resolved_inputs[key] = self.variable_resolver.resolve(value, context)

            elif isinstance(value, dict):
                # Recursively resolve dictionary values
                resolved_inputs[key] = self._resolve_step_inputs(value, context)
            elif isinstance(value, list):
                # Resolve list values
                resolved_inputs[key] = [
                    self.variable_resolver.resolve(item, context)
                    if isinstance(item, str) and "${" in item
                    else item
                    for item in value
                ]
            else:
                # Keep the value as-is
                resolved_inputs[key] = value

        return resolved_inputs

    async def _execute_system_action(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a system action step"""
        try:
            # Resolve step inputs with context
            resolved_inputs = self._resolve_step_inputs(step.inputs, context)

            action = step.action

            if action == "mock_data":
                # Return mock data for testing
                mock_data = resolved_inputs.get("mock_data", {})
                logger.info(f"Generated mock data for step '{step.name}': {mock_data}")
                return mock_data

            elif action == "log_completion":
                # Log workflow completion
                workflow_name = resolved_inputs.get("workflow_name", "Unknown")
                success = resolved_inputs.get("success", False)
                logger.info(
                    f"Workflow '{workflow_name}' completed with success: {success}"
                )
                return {
                    "logged": True,
                    "workflow_name": workflow_name,
                    "success": success,
                }

            elif action == "collect_metrics":
                # Mock metrics collection
                metrics = {
                    "execution_time": resolved_inputs.get("execution_time", "0s"),
                    "cost": resolved_inputs.get("cost", 0.0),
                    "success": resolved_inputs.get("success", False),
                }
                logger.info(f"Collected metrics: {metrics}")
                return metrics

            elif action == "log_workflow_completion":
                # Log detailed workflow completion
                results = resolved_inputs.get("results", {})
                logger.info(f"Workflow completion logged: {results}")
                return {"logged": True, "results": results}

            else:
                logger.warning(f"Unknown system action: {action}")
                return {"result": f"unknown_action_{action}"}

        except Exception as e:
            logger.error(f"Error executing system action '{step.name}': {e}")
            raise WorkflowExecutionError(f"System action failed: {e}")

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
