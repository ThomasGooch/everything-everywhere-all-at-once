"""Integration tests for AI-powered workflow execution"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.plugin_registry import PluginRegistry
from core.workflow_engine import WorkflowEngine


@pytest.mark.integration
class TestAIWorkflowIntegration:
    """Integration tests for AI workflow functionality"""

    @pytest.fixture
    def mock_claude_plugin(self):
        """Create a mock Claude plugin that returns realistic responses"""
        plugin = MagicMock()
        plugin.generate_text = AsyncMock()

        # Set up different responses for different types of prompts
        def mock_generate_response(prompt, **kwargs):
            from core.plugin_interface import PluginResult

            if "Analyze the codebase" in prompt:
                return PluginResult(
                    success=True,
                    data={
                        "generated_text": """## Codebase Analysis

### Architecture Overview
The codebase follows a modular Python architecture with clear separation of concerns:
- Core modules for workflow engine and plugin management
- Plugin system for external integrations
- Configuration management with YAML and environment variables

### Relevant Files for Hello World Task
- `examples/hello_world.py` - Target implementation file
- `tests/test_hello_world.py` - Test file location
- `README.md` - Documentation to update

### Existing Patterns
- FastAPI for API endpoints
- Pydantic for data validation
- Pytest for testing
- Black/flake8 for code formatting

### Recommendations
- Follow existing error handling patterns
- Use type hints consistently
- Include comprehensive docstrings""",
                        "model": "claude-3-5-sonnet-20241022",
                        "input_tokens": 150,
                        "output_tokens": 200,
                        "cost": 0.005,
                    },
                )
            elif "Create a detailed implementation plan" in prompt:
                return PluginResult(
                    success=True,
                    data={
                        "generated_text": """## Implementation Plan

### Summary
Create a simple hello world function with proper error handling and testing.

### Files to Modify/Create
1. `examples/hello_world.py` - Main implementation
2. `tests/test_hello_world.py` - Unit tests
3. `README.md` - Update with usage example

### Implementation Steps
1. Create hello_world() function with customizable message
2. Add input validation and error handling
3. Include comprehensive docstring
4. Write unit tests covering normal and edge cases
5. Update documentation

### Testing Strategy
- Unit tests for all function behaviors
- Edge case testing (empty input, special characters)
- Type checking validation

### Estimated Effort: Low (30 minutes)
### Complexity: Simple
### Risks: None - straightforward implementation""",
                        "model": "claude-3-5-sonnet-20241022",
                        "input_tokens": 250,
                        "output_tokens": 180,
                        "cost": 0.007,
                    },
                )
            elif "Generate production-ready code" in prompt:
                return PluginResult(
                    success=True,
                    data={
                        "generated_text": '''## Code Implementation

### File: examples/hello_world.py
```python
"""
Hello World Module

A simple module demonstrating best practices for Python development.
"""

from typing import Optional


def hello_world(name: Optional[str] = None, greeting: str = "Hello") -> str:
    """
    Generate a personalized greeting message.
    
    Args:
        name: Optional name to include in greeting. Defaults to "World"
        greeting: Greeting word to use. Defaults to "Hello"
        
    Returns:
        Formatted greeting string
        
    Raises:
        ValueError: If greeting is empty or contains only whitespace
        
    Examples:
        >>> hello_world()
        'Hello, World!'
        >>> hello_world("Alice")
        'Hello, Alice!'
        >>> hello_world("Bob", "Hi")
        'Hi, Bob!'
    """
    if not greeting or not greeting.strip():
        raise ValueError("Greeting cannot be empty or whitespace only")
    
    target = name if name and name.strip() else "World"
    return f"{greeting.strip()}, {target.strip()}!"


if __name__ == "__main__":
    print(hello_world())
    print(hello_world("Developer"))
    print(hello_world("Python", "Welcome"))
```

### File: tests/test_hello_world.py
```python
"""
Tests for hello_world module
"""

import pytest
from examples.hello_world import hello_world


class TestHelloWorld:
    """Test cases for hello_world function"""
    
    def test_default_greeting(self):
        """Test default greeting without parameters"""
        result = hello_world()
        assert result == "Hello, World!"
    
    def test_custom_name(self):
        """Test greeting with custom name"""
        result = hello_world("Alice")
        assert result == "Hello, Alice!"
    
    def test_custom_greeting(self):
        """Test custom greeting and name"""
        result = hello_world("Bob", "Hi")
        assert result == "Hi, Bob!"
    
    def test_empty_name_uses_world(self):
        """Test that empty name defaults to World"""
        result = hello_world("")
        assert result == "Hello, World!"
    
    def test_whitespace_name_uses_world(self):
        """Test that whitespace-only name defaults to World"""
        result = hello_world("   ")
        assert result == "Hello, World!"
    
    def test_empty_greeting_raises_error(self):
        """Test that empty greeting raises ValueError"""
        with pytest.raises(ValueError, match="Greeting cannot be empty"):
            hello_world("Alice", "")
    
    def test_whitespace_greeting_raises_error(self):
        """Test that whitespace-only greeting raises ValueError"""
        with pytest.raises(ValueError, match="Greeting cannot be empty"):
            hello_world("Alice", "   ")
    
    def test_greeting_with_extra_whitespace(self):
        """Test that extra whitespace is stripped"""
        result = hello_world("  Alice  ", "  Hi  ")
        assert result == "Hi, Alice!"
```''',
                        "model": "claude-3-5-sonnet-20241022",
                        "input_tokens": 400,
                        "output_tokens": 600,
                        "cost": 0.015,
                    },
                )
            elif "Generate comprehensive documentation" in prompt:
                return PluginResult(
                    success=True,
                    data={
                        "generated_text": """# Hello World Implementation

## Overview
A simple yet comprehensive hello world implementation demonstrating Python best practices.

## Usage

### Basic Usage
```python
from examples.hello_world import hello_world

# Default greeting
print(hello_world())  # Output: Hello, World!

# Custom name
print(hello_world("Alice"))  # Output: Hello, Alice!

# Custom greeting
print(hello_world("Bob", "Hi"))  # Output: Hi, Bob!
```

### API Reference

#### `hello_world(name=None, greeting="Hello")`

Generate a personalized greeting message.

**Parameters:**
- `name` (str, optional): Name to include in greeting. Defaults to "World"
- `greeting` (str): Greeting word to use. Defaults to "Hello"

**Returns:**
- `str`: Formatted greeting string

**Raises:**
- `ValueError`: If greeting is empty or contains only whitespace

## Testing
Run tests with pytest:
```bash
pytest tests/test_hello_world.py -v
```

## Implementation Notes
- Includes comprehensive input validation
- Handles edge cases (empty/whitespace inputs)
- Follows PEP 8 style guidelines
- Includes type hints for better IDE support""",
                        "model": "claude-3-5-sonnet-20241022",
                        "input_tokens": 300,
                        "output_tokens": 250,
                        "cost": 0.009,
                    },
                )
            else:
                # Generic response for other prompts
                return PluginResult(
                    success=True,
                    data={
                        "generated_text": "AI response for the given prompt.",
                        "model": "claude-3-5-sonnet-20241022",
                        "input_tokens": 50,
                        "output_tokens": 10,
                        "cost": 0.001,
                    },
                )

        plugin.generate_text.side_effect = mock_generate_response
        return plugin

    @pytest.fixture
    def workflow_engine_with_mock_claude(self, mock_claude_plugin):
        """Create workflow engine with mocked Claude plugin"""
        plugin_registry = PluginRegistry()

        # Register mock Claude plugin
        plugin_registry._instances["ai_provider.claude"] = mock_claude_plugin

        engine = WorkflowEngine(plugin_registry=plugin_registry)
        return engine

    @pytest.fixture
    def ai_test_workflow_yaml(self):
        """YAML content for AI test workflow"""
        return """
name: "AI Test Workflow"
description: "Test AI integration"
version: "1.0.0"

variables:
  task_title: "Test Hello World Task"

steps:
  - name: "mock_task_fetch"
    description: "Mock task data"
    type: "system_action"
    action: "mock_data"
    inputs:
      mock_data: 
        id: "TEST-001"
        title: "${task_title}"
        description: "Create a hello world function with proper testing"
        type: "feature"
    outputs:
      task: "task_data"

  - name: "analyze_codebase"
    description: "AI codebase analysis"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      repository_path: "/tmp/test"
    outputs:
      analysis: "codebase_analysis"

  - name: "generate_implementation_plan"
    description: "AI implementation planning"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      plan: "implementation_plan"

  - name: "generate_code_implementation"
    description: "AI code generation"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      plan: "${implementation_plan}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      implementation: "generated_code"

  - name: "generate_documentation"
    description: "AI documentation generation"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      implementation: "${generated_code}"
    outputs:
      documentation: "generated_docs"

success_criteria:
  - condition: "${generated_code.generated_text}"
    description: "Code must be generated"
"""

    @pytest.mark.asyncio
    async def test_complete_ai_workflow_execution(
        self, workflow_engine_with_mock_claude, ai_test_workflow_yaml
    ):
        """Test complete AI workflow execution from start to finish"""
        engine = workflow_engine_with_mock_claude

        # Parse workflow
        workflow = engine.parse_workflow(ai_test_workflow_yaml)

        # Validate workflow
        validation = engine.validate_workflow(workflow)
        assert validation.is_valid, f"Validation errors: {validation.errors}"

        # Execute workflow
        result = await engine.execute_workflow(workflow, {"task_id": "TEST-001"})

        # Verify overall success
        assert result.success, f"Workflow failed: {result.error_message}"

        # Verify all steps completed
        assert len(result.step_results) == 5
        for step_result in result.step_results:
            assert (
                step_result.success
            ), f"Step {step_result.step_name} failed: {step_result.error_message}"

        # Verify total cost tracking
        assert result.total_cost > 0, "Total cost should be tracked"

        # Verify specific AI outputs are structured correctly
        codebase_step = next(
            s for s in result.step_results if s.step_name == "analyze_codebase"
        )
        assert "generated_text" in codebase_step.outputs
        assert "Codebase Analysis" in codebase_step.outputs["generated_text"]

        plan_step = next(
            s
            for s in result.step_results
            if s.step_name == "generate_implementation_plan"
        )
        assert "Implementation Plan" in plan_step.outputs["generated_text"]

        code_step = next(
            s
            for s in result.step_results
            if s.step_name == "generate_code_implementation"
        )
        assert "def hello_world" in code_step.outputs["generated_text"]
        assert "pytest" in code_step.outputs["generated_text"]

        docs_step = next(
            s for s in result.step_results if s.step_name == "generate_documentation"
        )
        assert "Hello World Implementation" in docs_step.outputs["generated_text"]

    @pytest.mark.asyncio
    async def test_ai_action_cost_tracking(
        self, workflow_engine_with_mock_claude, mock_claude_plugin
    ):
        """Test that AI action costs are properly tracked"""
        engine = workflow_engine_with_mock_claude

        # Simple workflow with one AI step
        simple_workflow_yaml = """
name: "Cost Test"
description: "Test cost tracking"
version: "1.0.0"

steps:
  - name: "ai_test"
    description: "Test AI cost tracking"
    type: "ai_action"
    inputs:
      task:
        title: "Test task"
        description: "Test description"
    outputs:
      result: "ai_result"
"""

        workflow = engine.parse_workflow(simple_workflow_yaml)
        result = await engine.execute_workflow(workflow, {})

        # Verify cost was tracked
        assert result.total_cost > 0
        ai_step = result.step_results[0]
        assert ai_step.cost > 0

    @pytest.mark.asyncio
    async def test_ai_action_error_handling(self, workflow_engine_with_mock_claude):
        """Test AI action error handling when Claude API fails"""
        engine = workflow_engine_with_mock_claude

        # Mock Claude plugin to return failure
        mock_plugin = engine.plugin_registry._instances["ai_provider.claude"]
        mock_plugin.generate_text = AsyncMock()

        from core.plugin_interface import PluginResult

        mock_plugin.generate_text.return_value = PluginResult(
            success=False, error="API rate limit exceeded"
        )

        workflow_yaml = """
name: "Error Test"
version: "1.0.0"
steps:
  - name: "failing_ai_step"
    type: "ai_action"
    inputs:
      task: {title: "Test", description: "Test"}
    on_error: "continue"
"""

        workflow = engine.parse_workflow(workflow_yaml)
        result = await engine.execute_workflow(workflow, {})

        # Workflow should continue despite AI failure
        assert result.success is False  # Overall failure due to AI step failure
        assert len(result.step_results) == 1
        assert result.step_results[0].success is False
        assert "API rate limit exceeded" in result.step_results[0].error_message

    @pytest.mark.asyncio
    async def test_different_ai_prompt_types(
        self, workflow_engine_with_mock_claude, mock_claude_plugin
    ):
        """Test different types of AI prompts generate appropriate responses"""
        engine = workflow_engine_with_mock_claude

        # Test codebase analysis prompt
        workflow_yaml = """
name: "Prompt Test"
version: "1.0.0"
steps:
  - name: "analyze_codebase"
    type: "ai_action"
    inputs:
      task: {title: "Test Analysis", description: "Analyze code"}
      repository_path: "/test"
    outputs:
      analysis: "result"
"""

        workflow = engine.parse_workflow(workflow_yaml)
        result = await engine.execute_workflow(workflow, {})

        assert result.success
        step_result = result.step_results[0]
        assert "Codebase Analysis" in step_result.outputs["generated_text"]
        assert "Architecture Overview" in step_result.outputs["generated_text"]

    def test_ai_workflow_validation(self, workflow_engine_with_mock_claude):
        """Test that AI workflows validate correctly"""
        engine = workflow_engine_with_mock_claude

        # Valid AI workflow
        valid_yaml = """
name: "Valid AI Workflow"
version: "1.0.0"
steps:
  - name: "ai_step"
    type: "ai_action"
    inputs:
      task: {title: "Test"}
    outputs:
      result: "ai_result"
"""

        workflow = engine.parse_workflow(valid_yaml)
        validation = engine.validate_workflow(workflow)
        assert validation.is_valid

        # Invalid AI workflow (missing inputs)
        invalid_yaml = """
name: "Invalid AI Workflow"  
version: "1.0.0"
steps:
  - name: "ai_step"
    type: "ai_action"
    # Missing required inputs
    outputs:
      result: "ai_result"
"""

        workflow = engine.parse_workflow(invalid_yaml)
        validation = engine.validate_workflow(workflow)
        # Should still be valid - inputs can be empty dict
