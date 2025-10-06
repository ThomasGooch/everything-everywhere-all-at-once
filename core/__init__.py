"""AI Development Orchestrator Core Package - Clean Plugin System"""

__version__ = "2.0.0"
__description__ = "Clean AI-powered development automation platform"

from .exceptions import BaseSystemError, SecurityError, ValidationError
from .plugin_interface import BasePlugin, PluginType
from .plugin_registry import PluginRegistry

__all__ = [
    "BaseSystemError",
    "SecurityError",
    "ValidationError",
    "BasePlugin",
    "PluginType",
    "PluginRegistry",
]
