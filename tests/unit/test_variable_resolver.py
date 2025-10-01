"""
Test suite for the variable resolution system.

This test suite follows TDD methodology to implement the variable resolution
system that uses Jinja2 templates for complex variable substitution.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Import the classes we're going to implement
from core.variable_resolver import (
    VariableResolver,
    VariableContext,
    VariableResolutionError,
    TemplateFunction
)

class TestVariableResolver:
    """Unit tests for VariableResolver functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.resolver = VariableResolver()
        
        # Sample context for testing
        self.context = {
            "task": {
                "id": "TEST-123",
                "title": "Fix Login Bug",
                "status": "todo",
                "type": "feature",
                "priority": "high",
                "repository_url": "https://github.com/company/repo.git"
            },
            "project": {
                "name": "Test Project",
                "default_branch": "main",
                "tech_stack": ["python", "fastapi"],
                "team_channel": "#dev-team"
            },
            "system": {
                "timestamp": "2023-10-01T10:00:00Z",
                "agent_id": "agent-001",
                "workflow_id": "wf-123"
            },
            "user_defined": {
                "environment": "staging",
                "timeout": 300
            }
        }
    
    def test_variable_resolver_initialization(self):
        """Test that VariableResolver can be initialized properly"""
        # RED: This will fail since VariableResolver doesn't exist yet
        resolver = VariableResolver()
        assert resolver is not None
        assert hasattr(resolver, 'resolve')
        assert hasattr(resolver, 'create_context')
        
    def test_simple_variable_substitution(self):
        """Test simple variable substitution like ${task.id}"""
        # RED: This will fail since resolve method doesn't exist yet
        template = "Task ID is: ${task.id}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Task ID is: TEST-123"
        
    def test_nested_variable_access(self):
        """Test nested variable access like ${project.tech_stack.0}"""
        # RED: This will fail since nested access doesn't exist yet  
        template = "Primary technology: ${project.tech_stack.0}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Primary technology: python"
        
    def test_string_manipulation_functions(self):
        """Test string manipulation functions like lower(), upper(), replace()"""
        # RED: This will fail since string functions don't exist yet
        template = "Branch: feature/${task.title.lower().replace(' ', '-')}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Branch: feature/fix-login-bug"
        
    def test_conditional_expressions(self):
        """Test conditional expressions with if-else logic"""
        # RED: This will fail since conditional logic doesn't exist yet
        template = "Priority: ${task.priority if task.priority else 'medium'}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Priority: high"
        
        # Test with missing value
        context_no_priority = self.context.copy()
        del context_no_priority["task"]["priority"]
        result = self.resolver.resolve(template, context_no_priority)
        assert result == "Priority: medium"
        
    def test_complex_branch_name_generation(self):
        """Test complex branch name generation matching the standard workflow"""
        # Simplify to test individual parts that are realistic with Jinja2
        template = "feature/${task.id.lower()}-${task.title.lower().replace(' ', '-')}"
        result = self.resolver.resolve(template, self.context)
        # TEST-123 -> test-123, Fix Login Bug -> fix-login-bug
        assert result == "feature/test-123-fix-login-bug"
        
    def test_date_time_functions(self):
        """Test date/time template functions"""
        # RED: This will fail since date functions don't exist yet
        template = "Generated on: ${now().strftime('%Y-%m-%d %H:%M:%S')}"
        result = self.resolver.resolve(template, self.context)
        
        # Just check it contains a date-like pattern
        import re
        date_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        assert re.search(date_pattern, result)
        
    def test_json_operations(self):
        """Test JSON manipulation functions"""
        # RED: This will fail since JSON functions don't exist yet
        context_with_json = self.context.copy()
        context_with_json["config_json"] = '{"env": "staging", "debug": true}'
        
        template = "Environment: ${from_json(config_json).env}"
        result = self.resolver.resolve(template, context_with_json)
        assert result == "Environment: staging"
        
    def test_collection_operations(self):
        """Test collection manipulation functions like join, filter"""
        # RED: This will fail since collection functions don't exist yet
        template = "Technologies: ${project.tech_stack | join(', ')}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Technologies: python, fastapi"
        
    def test_default_values(self):
        """Test default value handling with || operator"""
        # RED: This will fail since default value logic doesn't exist yet
        template = "Channel: ${project.notification_channel || project.team_channel || '#general'}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Channel: #dev-team"
        
        # Test with all values missing
        minimal_context = {"project": {"name": "Test"}}
        result = self.resolver.resolve(template, minimal_context)
        assert result == "Channel: #general"
        
    def test_length_and_slicing_operations(self):
        """Test string length and slicing operations"""
        # RED: This will fail since length/slicing doesn't exist yet
        template = "Short title: ${task.title[:10]}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Short title: Fix Login "
        
        template2 = "Title length: ${len(task.title)}"
        result2 = self.resolver.resolve(template2, self.context)
        assert result2 == "Title length: 13"
        
    def test_variable_resolution_error_handling(self):
        """Test error handling for invalid variable references"""
        # RED: This will fail since error handling doesn't exist yet
        template = "${nonexistent.variable}"
        
        with pytest.raises(VariableResolutionError) as exc_info:
            self.resolver.resolve(template, self.context)
        
        assert "nonexistent" in str(exc_info.value)
        
    def test_safe_variable_access(self):
        """Test safe variable access that doesn't fail on missing keys"""
        # RED: This will fail since safe access doesn't exist yet
        template = "Value: ${task.missing_field | default('N/A')}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Value: N/A"
        
    def test_multiple_variable_substitution(self):
        """Test templates with multiple variable substitutions"""
        # RED: This will fail since multiple substitutions don't exist yet
        template = "${task.type}: ${task.title} (${task.id}) - Priority: ${task.priority}"
        result = self.resolver.resolve(template, self.context)
        assert result == "feature: Fix Login Bug (TEST-123) - Priority: high"
        
    def test_escape_sequences(self):
        """Test handling of escape sequences for literal ${ in templates"""
        # RED: This will fail since escape handling doesn't exist yet
        template = "Literal: $${not_a_variable} but this is: ${task.id}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Literal: ${not_a_variable} but this is: TEST-123"
        
    def test_whitespace_handling(self):
        """Test whitespace handling in templates"""
        # RED: This will fail since whitespace handling doesn't exist yet
        template = """
        Task: ${task.title}
        ID: ${task.id}
        """
        result = self.resolver.resolve(template, self.context)
        
        # Should preserve the structure but substitute variables
        assert "Fix Login Bug" in result
        assert "TEST-123" in result
        
    def test_variable_context_creation(self):
        """Test VariableContext creation and management"""
        # RED: This will fail since VariableContext doesn't exist yet
        context = VariableContext()
        context.set("task.id", "TEST-456")
        context.set("project.name", "New Project")
        
        template = "Working on ${task.id} in ${project.name}"
        result = self.resolver.resolve(template, context.to_dict())
        assert result == "Working on TEST-456 in New Project"
        
    def test_context_merging(self):
        """Test merging multiple contexts"""
        # RED: This will fail since context merging doesn't exist yet
        base_context = VariableContext({"env": "prod"})
        override_context = VariableContext({"env": "staging", "debug": True})
        
        merged = base_context.merge(override_context)
        template = "Running in ${env} with debug=${debug}"
        result = self.resolver.resolve(template, merged.to_dict())
        assert result == "Running in staging with debug=True"
        
    def test_custom_template_functions(self):
        """Test registration of custom template functions"""
        # RED: This will fail since custom functions don't exist yet
        def custom_hash(value):
            return f"hash_{hash(str(value)) % 1000}"
        
        self.resolver.register_function("custom_hash", custom_hash)
        
        template = "Hash: ${custom_hash(task.id)}"
        result = self.resolver.resolve(template, self.context)
        assert result.startswith("Hash: hash_")
        
    def test_template_function_class(self):
        """Test TemplateFunction class for complex functions"""
        # RED: This will fail since TemplateFunction doesn't exist yet
        class GitBranchFunction(TemplateFunction):
            def __call__(self, task_id, title):
                clean_title = title.lower().replace(' ', '-')
                return f"feature/{task_id.lower()}-{clean_title}"
        
        branch_func = GitBranchFunction()
        self.resolver.register_function("git_branch", branch_func)
        
        template = "Branch: ${git_branch(task.id, task.title)}"
        result = self.resolver.resolve(template, self.context)
        assert result == "Branch: feature/test-123-fix-login-bug"
        
    def test_performance_with_large_context(self):
        """Test performance with large variable contexts"""
        # RED: This will fail since performance optimizations don't exist yet
        large_context = self.context.copy()
        
        # Add lots of variables
        for i in range(1000):
            large_context[f"var_{i}"] = f"value_{i}"
        
        template = "Simple substitution: ${task.id}"
        
        # Should complete quickly even with large context
        import time
        start_time = time.time()
        result = self.resolver.resolve(template, large_context)
        duration = time.time() - start_time
        
        assert result == "Simple substitution: TEST-123"
        assert duration < 0.1  # Should complete in less than 100ms
        
    def test_recursive_variable_resolution(self):
        """Test recursive variable resolution"""
        # RED: This will fail since recursive resolution doesn't exist yet
        context = {
            "base_url": "https://api.example.com",
            "endpoint": "${base_url}/users",
            "full_url": "${endpoint}/123"
        }
        
        template = "Final URL: ${full_url}"
        result = self.resolver.resolve(template, context)
        assert result == "Final URL: https://api.example.com/users/123"
        
    def test_circular_reference_detection(self):
        """Test detection of circular variable references"""
        # RED: This will fail since circular detection doesn't exist yet
        context = {
            "var_a": "${var_b}",
            "var_b": "${var_a}"
        }
        
        template = "Value: ${var_a}"
        
        with pytest.raises(VariableResolutionError) as exc_info:
            self.resolver.resolve(template, context)
        
        assert "circular" in str(exc_info.value).lower()


class TestBuiltinTemplateFunctions:
    """Test suite for built-in template functions"""
    
    def setup_method(self):
        self.resolver = VariableResolver()
        
    def test_string_functions(self):
        """Test built-in string functions"""
        # RED: These will fail since built-in functions don't exist yet
        context = {"text": "Hello World"}
        
        # Test upper/lower
        assert self.resolver.resolve("${text.upper()}", context) == "HELLO WORLD"
        assert self.resolver.resolve("${text.lower()}", context) == "hello world"
        
        # Test replace
        assert self.resolver.resolve("${text.replace(' ', '_')}", context) == "Hello_World"
        
        # Test strip
        context2 = {"text": "  padded  "}
        assert self.resolver.resolve("${text.strip()}", context2) == "padded"
        
    def test_list_functions(self):
        """Test built-in list functions"""
        # RED: This will fail since list functions don't exist yet
        context = {"items": ["a", "b", "c"]}
        
        # Test join
        assert self.resolver.resolve("${items.join('-')}", context) == "a-b-c"
        
        # Test length
        assert self.resolver.resolve("${len(items)}", context) == "3"
        
        # Test indexing
        assert self.resolver.resolve("${items.0}", context) == "a"
        assert self.resolver.resolve("${items[1]}", context) == "b"
        
    def test_utility_functions(self):
        """Test utility template functions"""
        # RED: This will fail since utility functions don't exist yet
        context = {"data": '{"key": "value"}'}
        
        # Test JSON parsing
        result = self.resolver.resolve("${from_json(data).key}", context)
        assert result == "value"
        
        # Test UUID generation
        result = self.resolver.resolve("${uuid4()}", context)
        assert len(result) == 36  # Standard UUID length
        assert result.count('-') == 4
        
        # Test timestamp
        result = self.resolver.resolve("${timestamp()}", context)
        assert result.isdigit()  # Unix timestamp should be all digits