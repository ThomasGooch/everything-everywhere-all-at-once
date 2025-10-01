"""
Test suite for the workflow engine core module.

This test suite follows TDD methodology to implement the workflow engine
that can parse, validate, and execute YAML-based workflows.
"""

import pytest
import yaml
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

# Import the classes we're going to implement
from core.workflow_engine import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowResult,
    WorkflowValidationError,
    WorkflowExecutionError,
    StepResult,
    ErrorStrategy
)

class TestWorkflowEngine:
    """Unit tests for WorkflowEngine core functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.engine = WorkflowEngine()
        
        # Sample workflow YAML for testing
        self.simple_workflow_yaml = """
name: "Simple Test Workflow"
description: "A basic workflow for testing"
version: "1.0.0"

variables:
  test_var: "test_value"
  repository_url: "${task.repository_url}"

steps:
  - name: "test_step"
    description: "A test step"
    plugin: "task_management" 
    action: "get_task"
    inputs:
      task_id: "${task_id}"
    outputs:
      result: "task_data"
    on_error: "fail"
    timeout: 30
"""
        
        self.complex_workflow_yaml = """
name: "Complex Test Workflow"
description: "A complex workflow for testing advanced features"
version: "1.0.0"

variables:
  branch_name: "feature/${task.id}-${task.title.lower().replace(' ', '-')[:20]}"
  
prerequisites:
  - condition: "${task.status == 'todo'}"
    error_message: "Task must be in todo status"

steps:
  - name: "conditional_step"
    description: "A conditional step"
    plugin: "task_management"
    action: "update_task"
    condition: "${task.type == 'feature'}"
    inputs:
      task_id: "${task_id}"
      status: "in_progress"
    on_error: "retry"
    retry_count: 3
    
  - name: "parallel_steps"
    description: "Parallel step execution"
    type: "parallel"
    steps:
      - name: "step_a"
        plugin: "test_plugin"
        action: "action_a"
      - name: "step_b"
        plugin: "test_plugin"
        action: "action_b"

error_handling:
  default_strategy: "fail"
  step_overrides:
    conditional_step: "retry"

success_criteria:
  - condition: "${task_data.title}"
    description: "Task must have a title"
"""

    def test_workflow_engine_initialization(self):
        """Test that WorkflowEngine can be initialized properly"""
        # RED: This will fail since WorkflowEngine doesn't exist yet
        engine = WorkflowEngine()
        assert engine is not None
        assert hasattr(engine, 'parse_workflow')
        assert hasattr(engine, 'execute_workflow')
        assert hasattr(engine, 'validate_workflow')
    
    def test_parse_simple_workflow_yaml(self):
        """Test parsing a simple YAML workflow"""
        # RED: This will fail since parse_workflow doesn't exist yet
        workflow = self.engine.parse_workflow(self.simple_workflow_yaml)
        
        assert workflow.name == "Simple Test Workflow"
        assert workflow.description == "A basic workflow for testing"
        assert workflow.version == "1.0.0"
        assert len(workflow.steps) == 1
        assert workflow.variables["test_var"] == "test_value"
        assert workflow.variables["repository_url"] == "${task.repository_url}"
        
    def test_parse_complex_workflow_yaml(self):
        """Test parsing a complex YAML workflow with advanced features"""
        # RED: This will fail since the parsing logic doesn't exist yet
        workflow = self.engine.parse_workflow(self.complex_workflow_yaml)
        
        assert workflow.name == "Complex Test Workflow"
        assert len(workflow.prerequisites) == 1
        assert len(workflow.steps) == 2
        assert workflow.error_handling["default_strategy"] == "fail"
        assert len(workflow.success_criteria) == 1
        
    def test_parse_workflow_from_file(self):
        """Test parsing workflow from a YAML file"""
        # RED: This will fail since file parsing doesn't exist yet
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.simple_workflow_yaml)
            temp_file = f.name
            
        try:
            workflow = self.engine.load_workflow_from_file(temp_file)
            assert workflow.name == "Simple Test Workflow"
        finally:
            os.unlink(temp_file)
            
    def test_workflow_validation_success(self):
        """Test successful workflow validation"""
        # RED: This will fail since validation logic doesn't exist yet
        workflow = self.engine.parse_workflow(self.simple_workflow_yaml)
        validation_result = self.engine.validate_workflow(workflow)
        
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        
    def test_workflow_validation_failure(self):
        """Test workflow validation with errors"""
        # Test that parsing fails for empty name
        invalid_yaml = """
name: ""  # Invalid: empty name
steps:
  - name: "test_step"
    # Missing required fields: plugin, action
"""
        with pytest.raises(WorkflowValidationError) as exc_info:
            self.engine.parse_workflow(invalid_yaml)
        assert "name is required" in str(exc_info.value)
        
        # Test validation of workflow with missing plugin/action
        invalid_workflow_yaml = """
name: "Valid Name"
steps:
  - name: "test_step"
    # Missing required fields: plugin, action
"""
        workflow = self.engine.parse_workflow(invalid_workflow_yaml)
        validation_result = self.engine.validate_workflow(workflow)
        
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        
    def test_workflow_step_creation(self):
        """Test WorkflowStep object creation and properties"""
        # RED: This will fail since WorkflowStep doesn't exist yet
        step_data = {
            "name": "test_step",
            "description": "A test step",
            "plugin": "task_management",
            "action": "get_task",
            "inputs": {"task_id": "${task_id}"},
            "outputs": {"result": "task_data"},
            "on_error": "fail",
            "timeout": 30
        }
        
        step = WorkflowStep.from_dict(step_data)
        
        assert step.name == "test_step"
        assert step.description == "A test step"
        assert step.plugin == "task_management"
        assert step.action == "get_task"
        assert step.inputs == {"task_id": "${task_id}"}
        assert step.outputs == {"result": "task_data"}
        assert step.on_error == ErrorStrategy.FAIL
        assert step.timeout == 30
        
    def test_error_strategy_enum(self):
        """Test ErrorStrategy enum values"""
        # RED: This will fail since ErrorStrategy doesn't exist yet
        assert ErrorStrategy.FAIL.value == "fail"
        assert ErrorStrategy.RETRY.value == "retry"
        assert ErrorStrategy.CONTINUE.value == "continue"
        assert ErrorStrategy.ROLLBACK.value == "rollback"
        
    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """Test executing a simple workflow"""
        # RED: This will fail since execution logic doesn't exist yet
        workflow = self.engine.parse_workflow(self.simple_workflow_yaml)
        
        # Mock plugin registry and plugins
        with patch.object(self.engine, 'plugin_registry') as mock_registry:
            mock_plugin = AsyncMock()
            mock_plugin.get_task.return_value = {"id": "TEST-123", "title": "Test Task"}
            mock_registry.get_plugin_instance.return_value = mock_plugin
            
            context = {"task_id": "TEST-123"}
            result = await self.engine.execute_workflow(workflow, context)
            
            assert result.success is True
            assert result.workflow_name == "Simple Test Workflow"
            assert len(result.step_results) == 1
            assert result.step_results[0].success is True
            
    @pytest.mark.asyncio
    async def test_workflow_execution_with_failure(self):
        """Test workflow execution when a step fails"""
        # RED: This will fail since error handling doesn't exist yet
        workflow = self.engine.parse_workflow(self.simple_workflow_yaml)
        
        with patch.object(self.engine, 'plugin_registry') as mock_registry:
            mock_plugin = AsyncMock()
            mock_plugin.get_task.side_effect = Exception("Plugin failed")
            mock_registry.get_plugin_instance.return_value = mock_plugin
            
            context = {"task_id": "TEST-123"}
            result = await self.engine.execute_workflow(workflow, context)
            
            assert result.success is False
            assert len(result.step_results) == 1
            assert result.step_results[0].success is False
            assert "Plugin failed" in result.step_results[0].error_message
            
    @pytest.mark.asyncio 
    async def test_workflow_step_timeout(self):
        """Test workflow step timeout handling"""
        # RED: This will fail since timeout logic doesn't exist yet
        workflow_yaml = """
name: "Timeout Test"
steps:
  - name: "slow_step"
    plugin: "test_plugin"
    action: "slow_action"
    timeout: 1  # 1 second timeout
"""
        workflow = self.engine.parse_workflow(workflow_yaml)
        
        with patch.object(self.engine, 'plugin_registry') as mock_registry:
            mock_plugin = AsyncMock()
            # Simulate slow operation
            async def slow_operation(*args, **kwargs):
                await asyncio.sleep(2)  # Takes 2 seconds, timeout is 1 second
                return {"result": "success"}
                
            mock_plugin.slow_action = slow_operation
            mock_registry.get_plugin_instance.return_value = mock_plugin
            
            result = await self.engine.execute_workflow(workflow, {})
            
            assert result.success is False
            assert "timeout" in result.step_results[0].error_message.lower()
            
    def test_workflow_variable_references(self):
        """Test that workflow properly identifies variable references"""
        # RED: This will fail since variable parsing doesn't exist yet
        workflow = self.engine.parse_workflow(self.complex_workflow_yaml)
        
        # Check that variable references are identified
        step = workflow.steps[0]  # conditional_step
        assert "${task_id}" in str(step.inputs)
        
        # Check that complex variable expressions are handled
        branch_name_var = workflow.variables["branch_name"]
        assert "${task.id}" in branch_name_var
        assert "${task.title.lower().replace(' ', '-')[:20]}" in branch_name_var
        
    def test_workflow_prerequisites_parsing(self):
        """Test parsing of workflow prerequisites"""
        # RED: This will fail since prerequisite parsing doesn't exist yet
        workflow = self.engine.parse_workflow(self.complex_workflow_yaml)
        
        assert len(workflow.prerequisites) == 1
        prerequisite = workflow.prerequisites[0]
        assert prerequisite["condition"] == "${task.status == 'todo'}"
        assert prerequisite["error_message"] == "Task must be in todo status"
        
    def test_parallel_steps_parsing(self):
        """Test parsing of parallel step execution"""
        # RED: This will fail since parallel step parsing doesn't exist yet
        workflow = self.engine.parse_workflow(self.complex_workflow_yaml)
        
        parallel_step = workflow.steps[1]  # parallel_steps
        assert parallel_step.type == "parallel"
        assert len(parallel_step.parallel_steps) == 2
        assert parallel_step.parallel_steps[0].name == "step_a"
        assert parallel_step.parallel_steps[1].name == "step_b"
        
    def test_conditional_step_parsing(self):
        """Test parsing of conditional steps"""
        # RED: This will fail since conditional parsing doesn't exist yet
        workflow = self.engine.parse_workflow(self.complex_workflow_yaml)
        
        conditional_step = workflow.steps[0]  # conditional_step
        assert conditional_step.condition == "${task.type == 'feature'}"
        assert conditional_step.on_error == ErrorStrategy.RETRY
        assert conditional_step.retry_count == 3
        
    def test_workflow_result_object(self):
        """Test WorkflowResult object properties"""
        # RED: This will fail since WorkflowResult doesn't exist yet
        step_results = [
            StepResult(
                step_name="test_step",
                success=True,
                duration=timedelta(seconds=5),
                outputs={"result": "success"}
            )
        ]
        
        result = WorkflowResult(
            workflow_name="Test Workflow",
            success=True,
            step_results=step_results,
            execution_time=timedelta(seconds=10),
            total_cost=5.50
        )
        
        assert result.workflow_name == "Test Workflow"
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.execution_time.total_seconds() == 10
        assert result.total_cost == 5.50
        
    def test_step_result_object(self):
        """Test StepResult object properties"""
        # RED: This will fail since StepResult doesn't exist yet
        step_result = StepResult(
            step_name="test_step",
            success=True,
            duration=timedelta(seconds=5),
            outputs={"result": "success"},
            error_message=None,
            retry_count=0
        )
        
        assert step_result.step_name == "test_step"
        assert step_result.success is True
        assert step_result.duration.total_seconds() == 5
        assert step_result.outputs == {"result": "success"}
        assert step_result.error_message is None
        assert step_result.retry_count == 0
        
    def test_workflow_engine_plugin_integration(self):
        """Test that workflow engine integrates with plugin registry"""
        # RED: This will fail since plugin integration doesn't exist yet
        from core.plugin_registry import PluginRegistry
        
        plugin_registry = PluginRegistry()
        engine = WorkflowEngine(plugin_registry=plugin_registry)
        
        assert engine.plugin_registry is not None
        assert engine.plugin_registry == plugin_registry


class TestWorkflowValidation:
    """Test suite for workflow validation logic"""
    
    def setup_method(self):
        self.engine = WorkflowEngine()
        
    def test_validate_required_fields(self):
        """Test validation of required workflow fields"""
        # RED: This will fail since validation doesn't exist yet
        invalid_workflow = """
# Missing name
description: "Test workflow"
steps: []
"""
        
        with pytest.raises(WorkflowValidationError) as exc_info:
            self.engine.parse_workflow(invalid_workflow)
            
        assert "name is required" in str(exc_info.value)
        
    def test_validate_step_dependencies(self):
        """Test validation of step dependencies"""
        # RED: This will fail since dependency validation doesn't exist yet
        workflow_with_dependencies = """
name: "Dependency Test"
steps:
  - name: "step_2"
    plugin: "test"
    action: "test"
    inputs:
      data: "${step_1.output}"  # References step_1 but step_1 doesn't exist
"""
        
        workflow = self.engine.parse_workflow(workflow_with_dependencies)
        validation_result = self.engine.validate_workflow(workflow)
        
        assert validation_result.is_valid is False
        assert any("step_1" in error for error in validation_result.errors)
        
    def test_validate_circular_dependencies(self):
        """Test detection of circular dependencies"""
        # RED: This will fail since circular dependency detection doesn't exist yet
        circular_workflow = """
name: "Circular Dependency Test"
steps:
  - name: "step_1"
    plugin: "test"
    action: "test"
    inputs:
      data: "${step_2.output}"
  - name: "step_2"  
    plugin: "test"
    action: "test"
    inputs:
      data: "${step_1.output}"
"""
        
        workflow = self.engine.parse_workflow(circular_workflow)
        validation_result = self.engine.validate_workflow(workflow)
        
        assert validation_result.is_valid is False
        assert any("circular dependency" in error.lower() for error in validation_result.errors)
        
    def test_validate_plugin_actions(self):
        """Test validation of plugin actions against registered plugins"""
        # RED: This will fail since plugin validation doesn't exist yet
        workflow_yaml = """
name: "Plugin Validation Test"
steps:
  - name: "invalid_step"
    plugin: "nonexistent_plugin"
    action: "invalid_action"
"""
        
        workflow = self.engine.parse_workflow(workflow_yaml)
        
        # Mock plugin registry to return no plugins
        with patch.object(self.engine, 'plugin_registry') as mock_registry:
            mock_registry.get_plugin_instance.return_value = None
            
            validation_result = self.engine.validate_workflow(workflow)
            
            assert validation_result.is_valid is False
            assert any("nonexistent_plugin" in error for error in validation_result.errors)


# Import asyncio for async tests
import asyncio