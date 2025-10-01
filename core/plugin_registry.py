"""Plugin registry for managing plugin discovery, loading, and lifecycle"""

from typing import Dict, List, Optional, Type, Any, Set
import importlib
import inspect
import logging
from pathlib import Path

from .plugin_interface import BasePlugin, PluginType, PluginError, PluginValidationError

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing all plugins"""
    
    def __init__(self):
        """Initialize plugin registry"""
        self._plugins: Dict[str, Dict[str, Type[BasePlugin]]] = {}
        self._instances: Dict[str, BasePlugin] = {}
        self._plugin_paths: List[Path] = []
        
        # Initialize plugin type dictionaries
        for plugin_type in PluginType:
            self._plugins[plugin_type.value] = {}
    
    def register_plugin(self, plugin_type: PluginType, plugin_name: str, plugin_class: Type[BasePlugin]):
        """Register a plugin class
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Unique name for the plugin
            plugin_class: Plugin class to register
            
        Raises:
            PluginValidationError: If plugin class is invalid
        """
        # Validate plugin class
        if not issubclass(plugin_class, BasePlugin):
            raise PluginValidationError(f"Plugin class {plugin_class} must inherit from BasePlugin")
        
        if not hasattr(plugin_class, 'get_plugin_type') or not hasattr(plugin_class, 'get_plugin_name'):
            raise PluginValidationError(f"Plugin class {plugin_class} must implement required methods")
        
        plugin_type_str = plugin_type.value
        
        if plugin_name in self._plugins[plugin_type_str]:
            logger.warning(f"Plugin {plugin_type_str}.{plugin_name} already registered, overwriting")
        
        self._plugins[plugin_type_str][plugin_name] = plugin_class
        logger.info(f"Registered plugin: {plugin_type_str}.{plugin_name}")
    
    def get_plugin_class(self, plugin_type: PluginType, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """Get plugin class by type and name
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Plugin name
            
        Returns:
            Plugin class if found, None otherwise
        """
        plugin_type_str = plugin_type.value
        return self._plugins.get(plugin_type_str, {}).get(plugin_name)
    
    def create_plugin_instance(self, plugin_type: PluginType, plugin_name: str, config: Dict[str, Any]) -> BasePlugin:
        """Create plugin instance with configuration
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Plugin name
            config: Plugin configuration
            
        Returns:
            Configured plugin instance
            
        Raises:
            PluginError: If plugin not found or creation fails
        """
        plugin_class = self.get_plugin_class(plugin_type, plugin_name)
        if plugin_class is None:
            raise PluginError(f"Plugin {plugin_type.value}.{plugin_name} not found")
        
        try:
            instance = plugin_class(config)
            
            # Validate configuration
            if not instance.validate_config():
                raise PluginValidationError(f"Invalid configuration for plugin {plugin_type.value}.{plugin_name}")
            
            plugin_id = f"{plugin_type.value}.{plugin_name}"
            self._instances[plugin_id] = instance
            
            logger.info(f"Created plugin instance: {plugin_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create plugin instance {plugin_type.value}.{plugin_name}: {e}")
            raise PluginError(f"Failed to create plugin: {e}") from e
    
    def get_plugin_instance(self, plugin_type: PluginType, plugin_name: str) -> Optional[BasePlugin]:
        """Get existing plugin instance
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Plugin name
            
        Returns:
            Plugin instance if exists, None otherwise
        """
        plugin_id = f"{plugin_type.value}.{plugin_name}"
        return self._instances.get(plugin_id)
    
    def list_plugins(self, plugin_type: Optional[PluginType] = None) -> Dict[str, List[str]]:
        """List all registered plugins
        
        Args:
            plugin_type: Optional filter by plugin type
            
        Returns:
            Dictionary mapping plugin types to plugin names
        """
        if plugin_type:
            plugin_type_str = plugin_type.value
            return {plugin_type_str: list(self._plugins.get(plugin_type_str, {}).keys())}
        
        return {
            plugin_type: list(plugins.keys()) 
            for plugin_type, plugins in self._plugins.items()
        }
    
    def discover_plugins(self, plugin_path: Path) -> int:
        """Discover and auto-register plugins from directory
        
        Args:
            plugin_path: Path to search for plugin modules
            
        Returns:
            Number of plugins discovered and registered
        """
        if not plugin_path.exists() or not plugin_path.is_dir():
            logger.warning(f"Plugin path {plugin_path} does not exist or is not a directory")
            return 0
        
        discovered_count = 0
        self._plugin_paths.append(plugin_path)
        
        # Look for Python files in the plugin directory
        for py_file in plugin_path.glob("*_plugin.py"):
            try:
                # Import the module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for plugin classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BasePlugin) and 
                            obj != BasePlugin):
                            
                            try:
                                # Create temporary instance to get metadata
                                temp_instance = obj({})
                                plugin_type = temp_instance.get_plugin_type()
                                plugin_name = temp_instance.get_plugin_name()
                                
                                self.register_plugin(plugin_type, plugin_name, obj)
                                discovered_count += 1
                                
                            except Exception as e:
                                logger.error(f"Failed to register discovered plugin {name}: {e}")
                                
            except Exception as e:
                logger.error(f"Failed to load plugin module {py_file}: {e}")
        
        logger.info(f"Discovered {discovered_count} plugins from {plugin_path}")
        return discovered_count
    
    async def initialize_all_plugins(self) -> Dict[str, bool]:
        """Initialize all plugin instances
        
        Returns:
            Dictionary mapping plugin IDs to initialization success status
        """
        results = {}
        
        for plugin_id, plugin_instance in self._instances.items():
            try:
                success = await plugin_instance.initialize()
                results[plugin_id] = success
                
                if success:
                    logger.info(f"Successfully initialized plugin: {plugin_id}")
                else:
                    logger.error(f"Failed to initialize plugin: {plugin_id}")
                    
            except Exception as e:
                logger.error(f"Exception initializing plugin {plugin_id}: {e}")
                results[plugin_id] = False
        
        return results
    
    async def cleanup_all_plugins(self) -> Dict[str, bool]:
        """Cleanup all plugin instances
        
        Returns:
            Dictionary mapping plugin IDs to cleanup success status
        """
        results = {}
        
        for plugin_id, plugin_instance in self._instances.items():
            try:
                success = await plugin_instance.cleanup()
                results[plugin_id] = success
                
                if success:
                    logger.info(f"Successfully cleaned up plugin: {plugin_id}")
                else:
                    logger.error(f"Failed to cleanup plugin: {plugin_id}")
                    
            except Exception as e:
                logger.error(f"Exception cleaning up plugin {plugin_id}: {e}")
                results[plugin_id] = False
        
        return results
    
    async def health_check_all_plugins(self) -> Dict[str, str]:
        """Perform health check on all plugin instances
        
        Returns:
            Dictionary mapping plugin IDs to health status
        """
        results = {}
        
        for plugin_id, plugin_instance in self._instances.items():
            try:
                status = await plugin_instance.health_check()
                results[plugin_id] = status.value
                
            except Exception as e:
                logger.error(f"Exception during health check for plugin {plugin_id}: {e}")
                results[plugin_id] = "unknown"
        
        return results
    
    def get_plugin_info(self, plugin_type: Optional[PluginType] = None) -> Dict[str, Any]:
        """Get information about registered plugins
        
        Args:
            plugin_type: Optional filter by plugin type
            
        Returns:
            Dictionary containing plugin information
        """
        info = {
            "total_registered": sum(len(plugins) for plugins in self._plugins.values()),
            "total_instances": len(self._instances),
            "plugin_paths": [str(p) for p in self._plugin_paths],
            "plugins_by_type": {}
        }
        
        # Add detailed plugin information
        for ptype_str, plugins in self._plugins.items():
            if plugin_type and ptype_str != plugin_type.value:
                continue
                
            info["plugins_by_type"][ptype_str] = {
                "registered_count": len(plugins),
                "plugins": list(plugins.keys()),
                "instances": []
            }
            
            # Add instance information
            for plugin_name in plugins.keys():
                plugin_id = f"{ptype_str}.{plugin_name}"
                if plugin_id in self._instances:
                    instance_info = self._instances[plugin_id].get_plugin_info()
                    info["plugins_by_type"][ptype_str]["instances"].append(instance_info)
        
        return info