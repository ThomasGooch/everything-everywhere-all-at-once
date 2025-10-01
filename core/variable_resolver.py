"""
Variable Resolution System

This module provides comprehensive variable resolution using Jinja2 templates
with custom functions and safe variable access patterns. It supports:

- Simple variable substitution (${var.field})
- Complex expressions with string manipulation
- Conditional logic and default values
- Custom template functions
- Safe variable access with error handling
- Performance optimization for large contexts
"""

import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from jinja2 import Environment, DictLoader, select_autoescape, TemplateError, TemplateSyntaxError

import logging

logger = logging.getLogger(__name__)


class VariableResolutionError(Exception):
    """Raised when variable resolution fails"""
    pass


class TemplateFunction:
    """Base class for complex template functions"""
    
    def __call__(self, *args, **kwargs):
        """Override this method in subclasses"""
        raise NotImplementedError("Template function must implement __call__")


class VariableContext:
    """Manages variable contexts with merging and safe access"""
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize variable context"""
        self._data = initial_data.copy() if initial_data else {}
    
    def set(self, key: str, value: Any):
        """Set a variable using dot notation (e.g., 'task.id')"""
        keys = key.split('.')
        current = self._data
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                raise VariableResolutionError(f"Cannot set '{key}': '{k}' is not a dictionary")
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable using dot notation"""
        keys = key.split('.')
        current = self._data
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def merge(self, other: 'VariableContext') -> 'VariableContext':
        """Merge with another context, with other taking precedence"""
        merged_data = self._deep_merge(self._data, other._data)
        return VariableContext(merged_data)
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return self._data.copy()


class VariableResolver:
    """
    Advanced variable resolution system using Jinja2 templates with custom functions
    """
    
    def __init__(self):
        """Initialize the variable resolver with Jinja2 environment"""
        self.jinja_env = Environment(
            loader=DictLoader({}),
            autoescape=select_autoescape(['html', 'xml']),
            # Enable expression statements for more flexible templates
            # But keep it safe for security
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register built-in functions
        self._register_builtin_functions()
        
        # Track circular references
        self._resolution_stack = set()
        
        # Performance tracking
        self._resolution_cache = {}
        
    def resolve(self, template_string: str, context: Dict[str, Any], 
                enable_cache: bool = True) -> str:
        """
        Resolve variables in a template string using the provided context
        
        Args:
            template_string: Template string with variable placeholders
            context: Variable context dictionary
            enable_cache: Whether to use template caching for performance
            
        Returns:
            Resolved string with variables substituted
            
        Raises:
            VariableResolutionError: If resolution fails
        """
        if not template_string:
            return template_string
            
        try:
            # Check cache first
            cache_key = hash(template_string) if enable_cache else None
            if cache_key and cache_key in self._resolution_cache:
                template = self._resolution_cache[cache_key]
            else:
                # Convert ${var} syntax to Jinja2 {{var}} syntax
                jinja_template_string = self._convert_to_jinja_syntax(template_string)
                
                # Create and compile template
                template = self.jinja_env.from_string(jinja_template_string)
                
                if enable_cache:
                    self._resolution_cache[cache_key] = template
            
            # Prepare context with built-in variables and functions
            enhanced_context = self._prepare_context(context)
            
            # Resolve recursively to handle variable references within variables
            resolved_context = self._resolve_recursive_variables(enhanced_context)
            
            # Render the template
            result = template.render(**resolved_context)
            
            return result
            
        except TemplateSyntaxError as e:
            raise VariableResolutionError(f"Template syntax error: {e}")
        except TemplateError as e:
            raise VariableResolutionError(f"Template rendering error: {e}")
        except Exception as e:
            raise VariableResolutionError(f"Variable resolution failed: {e}")
    
    def _convert_to_jinja_syntax(self, template_string: str) -> str:
        """Convert ${var} syntax to Jinja2 {{var}} syntax"""
        # Handle escaped $$ sequences first
        escaped = template_string.replace('$$', '__ESCAPED_DOLLAR__')
        
        # Convert ${variable} to {{ variable }}
        # Use regex to handle nested braces properly
        pattern = r'\$\{([^}]+)\}'
        
        def replace_match(match):
            content = match.group(1)
            
            # Handle default values with || operator
            if ' || ' in content:
                parts = [part.strip() for part in content.split(' || ')]
                # Convert to Jinja2 default filter syntax
                base_var = parts[0]
                default_chain = parts[1:]
                
                # Process the base var for method calls first
                base_var = self._convert_method_calls(base_var)
                
                # Build nested default expressions
                result = base_var
                for default in default_chain:
                    # If default looks like a string (quoted), use it directly
                    if default.startswith("'") and default.endswith("'"):
                        result = f"({result} or {default})"
                    else:
                        # It might be another variable, add proper fallback
                        result = f"({result} or {default})"
                
                return f"{{{{ {result} }}}}"
            else:
                # Convert method calls in the content
                content = self._convert_method_calls(content)
                return f"{{{{ {content} }}}}"
        
        converted = re.sub(pattern, replace_match, escaped)
        
        # Restore escaped dollar signs - but only for non-variable sequences
        converted = converted.replace('__ESCAPED_DOLLAR__', '$')
        
        return converted
    
    def _convert_method_calls(self, content: str) -> str:
        """Convert Python-style method calls to Jinja2 filters or expressions"""
        
        # Handle slicing operations first (before other method calls)
        content = re.sub(r'(\[:[^\]]*\])', r'\1', content)  # Handle slicing like [:30]
        
        # Handle method chaining by converting to pipe syntax
        # This is complex because we need to handle chained methods
        # For now, handle simpler cases and common patterns from the workflow
        
        # Handle specific complex cases like task.title.lower().replace(' ', '-')[:30]
        # Convert to Jinja2 filter chain syntax
        
        # Pattern for: var.lower().replace(a, b)[:n]
        pattern = r"(\w+(?:\.\w+)*?)\.lower\(\)\.replace\('([^']+)',\s*'([^']+)'\)\[:(\d+)\]"
        replacement = r'(\1|lower|replace("\2", "\3"))[:(\4|int)]'
        content = re.sub(pattern, replacement, content)
        
        # Pattern for: var.lower().replace(a, b).replace(c, d)[:n]  
        pattern2 = r"(\w+(?:\.\w+)*?)\.lower\(\)\.replace\('([^']+)',\s*'([^']+)'\)\.replace\('([^']+)',\s*'([^']+)'\)\[:(\d+)\]"
        replacement2 = r'(\1|lower|replace("\2", "\3")|replace("\4", "\5"))[:(\6|int)]'
        content = re.sub(pattern2, replacement2, content)
        
        # Handle individual method calls
        method_mappings = {
            r'(\w+)\.join\(([^)]+)\)': r'\1|join(\2)',
            r'(\w+)\.upper\(\)': r'\1|upper',
            r'(\w+)\.lower\(\)': r'\1|lower', 
            r'(\w+)\.strip\(\)': r'\1|trim',
            r'(\w+)\.replace\(([^,]+),\s*([^)]+)\)': r'\1|replace(\2, \3)',
            r'len\(([^)]+)\)': r'\1|length',
        }
        
        # Apply method mappings
        for pattern, replacement in method_mappings.items():
            content = re.sub(pattern, replacement, content)
        
        # Handle list indexing like items.0 or items[0]  
        content = re.sub(r'(\w+)\.(\d+)', r'\1[\2]', content)
        
        return content
    
    def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context with built-in variables and functions"""
        enhanced_context = context.copy()
        
        # Add system variables if not present
        if 'system' not in enhanced_context:
            enhanced_context['system'] = {}
        
        # Add current timestamp
        enhanced_context['system']['current_timestamp'] = datetime.utcnow().isoformat()
        enhanced_context['system']['unix_timestamp'] = int(time.time())
        
        return enhanced_context
    
    def _resolve_recursive_variables(self, context: Dict[str, Any], 
                                   max_depth: int = 5) -> Dict[str, Any]:
        """Resolve variables that reference other variables recursively"""
        resolved = context.copy()
        changes_made = True
        depth = 0
        
        # Track what we've seen to detect circular references
        previous_states = []
        
        while changes_made and depth < max_depth:
            changes_made = False
            depth += 1
            
            # Check for circular references by comparing with previous states
            current_state = {k: v for k, v in resolved.items() if isinstance(v, str) and '${' in v}
            if current_state in previous_states:
                # Found a circular reference
                circular_vars = list(current_state.keys())
                raise VariableResolutionError(f"Circular reference detected in variables: {circular_vars}")
            
            previous_states.append(current_state.copy())
            
            for key, value in list(resolved.items()):
                if isinstance(value, str) and '${' in value:
                    try:
                        # Try to resolve this value
                        new_value = self._simple_resolve(value, resolved)
                        if new_value != value:
                            resolved[key] = new_value
                            changes_made = True
                    except Exception:
                        # If resolution fails, leave the value as is
                        pass
        
        # If we hit max_depth, check if there are still unresolved variables with ${
        if depth >= max_depth:
            unresolved = [k for k, v in resolved.items() if isinstance(v, str) and '${' in v]
            if unresolved:
                raise VariableResolutionError(f"Maximum recursion depth exceeded, possible circular reference in: {unresolved}")
        
        # Also check for any remaining variables that reference themselves directly
        for key, value in resolved.items():
            if isinstance(value, str) and f"${{{key}}}" in value:
                raise VariableResolutionError(f"Circular reference detected in variable: {key}")
        
        return resolved
    
    def _simple_resolve(self, template: str, context: Dict[str, Any]) -> str:
        """Simple variable resolution without recursion"""
        # Convert ${var} to Jinja2 syntax and resolve
        jinja_template = self._convert_to_jinja_syntax(template)
        try:
            template_obj = self.jinja_env.from_string(jinja_template)
            return template_obj.render(**context)
        except Exception:
            # If resolution fails, return original
            return template
    
    def register_function(self, name: str, func: Union[Callable, TemplateFunction]):
        """Register a custom template function"""
        self.jinja_env.globals[name] = func
    
    def create_context(self, **kwargs) -> VariableContext:
        """Create a new variable context"""
        return VariableContext(kwargs)
    
    def _register_builtin_functions(self):
        """Register built-in template functions"""
        
        # Global functions
        self.jinja_env.globals.update({
            # Date/time functions
            'now': lambda: datetime.utcnow(),
            'timestamp': lambda: str(int(time.time())),
            
            # JSON functions
            'from_json': lambda s: json.loads(s) if isinstance(s, str) else s,
            'to_json': lambda obj: json.dumps(obj),
            
            # UUID function
            'uuid4': lambda: str(uuid.uuid4()),
            
            # Length function (Jinja2 has len but we ensure it's available)
            'len': len,
        })
        
        # Don't override Jinja2's built-in default filter
        # It already handles None and undefined variables correctly
        
        # Enable do extension to allow method calls
        self.jinja_env.add_extension('jinja2.ext.do')
    
    def _default_filter(self, value, default_value=''):
        """Custom default filter that handles None and empty strings"""
        if value is None or value == '':
            return default_value
        return value