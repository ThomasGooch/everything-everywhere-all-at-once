"""AI Development Orchestrator Core Package"""

__version__ = "0.1.0"
__description__ = "Universal AI-powered development automation platform"

from .agent_context import AgentContext
from .config import ConfigManager, Settings
from .plugin_interface import BasePlugin, PluginType
from .plugin_registry import PluginRegistry

__all__ = [
    "AgentContext",
    "BasePlugin",
    "PluginType",
    "PluginRegistry",
    "ConfigManager",
    "Settings",
]
