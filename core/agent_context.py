"""Central orchestrator for managing the AI Development Automation System"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ConfigManager, Settings
from .plugin_interface import BasePlugin, PluginError, PluginType
from .plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class AgentContextError(Exception):
    """Base exception for AgentContext operations"""

    pass


class AgentContext:
    """Central orchestrator for the AI Development Automation System

    This class manages:
    - Plugin lifecycle and registry
    - Configuration loading and distribution
    - System initialization and cleanup
    - Inter-component communication
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize AgentContext

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_manager = ConfigManager(config_dir)
        self.plugin_registry = PluginRegistry()
        self._settings: Optional[Settings] = None
        self._initialized = False
        self._plugins_initialized = False

        # Component tracking
        self._active_agents: Dict[str, Any] = {}
        self._active_workspaces: Dict[str, Any] = {}

        logger.info("AgentContext initialized")

    @property
    def settings(self) -> Settings:
        """Get application settings"""
        if self._settings is None:
            self._settings = self.config_manager.get_settings()
        return self._settings

    @property
    def is_initialized(self) -> bool:
        """Check if AgentContext is fully initialized"""
        return self._initialized and self._plugins_initialized

    async def initialize(self, plugin_paths: Optional[List[Path]] = None) -> bool:
        """Initialize the AgentContext and all components

        Args:
            plugin_paths: Optional list of paths to discover plugins from

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing AgentContext...")

            # Load settings
            self._settings = self.config_manager.get_settings()
            logger.info(f"Loaded settings for environment: {self.settings.environment}")

            # Discover and register plugins
            if plugin_paths:
                for plugin_path in plugin_paths:
                    discovered = self.plugin_registry.discover_plugins(plugin_path)
                    logger.info(f"Discovered {discovered} plugins from {plugin_path}")

            # Create plugin instances from configuration
            await self._create_configured_plugins()

            # Initialize all plugins
            plugin_init_results = await self.plugin_registry.initialize_all_plugins()
            failed_plugins = [
                pid for pid, success in plugin_init_results.items() if not success
            ]

            if failed_plugins:
                logger.error(f"Failed to initialize plugins: {failed_plugins}")
                # Continue with partial initialization - some plugins may not be
                # critical

            self._plugins_initialized = True

            # Perform system health check
            await self._initial_health_check()

            self._initialized = True
            logger.info("AgentContext initialization completed successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize AgentContext: {e}")
            self._initialized = False
            raise AgentContextError(f"Initialization failed: {e}") from e

    async def cleanup(self) -> bool:
        """Cleanup all resources and shutdown gracefully

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info("Cleaning up AgentContext...")

            # Cleanup active agents and workspaces
            await self._cleanup_active_resources()

            # Cleanup all plugins
            if self._plugins_initialized:
                plugin_cleanup_results = (
                    await self.plugin_registry.cleanup_all_plugins()
                )
                failed_cleanups = [
                    pid
                    for pid, success in plugin_cleanup_results.items()
                    if not success
                ]

                if failed_cleanups:
                    logger.warning(f"Failed to cleanup plugins: {failed_cleanups}")

            self._initialized = False
            self._plugins_initialized = False

            logger.info("AgentContext cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

    async def get_plugin(
        self, plugin_type: PluginType, plugin_name: str
    ) -> Optional[BasePlugin]:
        """Get plugin instance by type and name

        Args:
            plugin_type: Type of plugin
            plugin_name: Plugin name

        Returns:
            Plugin instance if found, None otherwise
        """
        return self.plugin_registry.get_plugin_instance(plugin_type, plugin_name)

    async def create_plugin_instance(
        self,
        plugin_type: PluginType,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BasePlugin:
        """Create and configure plugin instance

        Args:
            plugin_type: Type of plugin
            plugin_name: Plugin name
            config: Optional plugin configuration (uses default if not provided)

        Returns:
            Configured plugin instance

        Raises:
            PluginError: If plugin creation fails
        """
        if config is None:
            # Get configuration from config manager
            config = self.config_manager.get_plugin_config(plugin_name)

        if not config:
            raise PluginError(f"No configuration found for plugin {plugin_name}")

        try:
            plugin_instance = self.plugin_registry.create_plugin_instance(
                plugin_type, plugin_name, config
            )

            # Initialize the plugin immediately
            success = await plugin_instance.initialize()
            if not success:
                raise PluginError(
                    f"Failed to initialize plugin {plugin_type.value}.{plugin_name}"
                )

            logger.info(
                f"Created and initialized plugin: {plugin_type.value}.{plugin_name}"
            )
            return plugin_instance

        except Exception as e:
            logger.error(f"Failed to create plugin instance: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check

        Returns:
            Dictionary containing health status information
        """
        health_status = {
            "overall_status": "healthy",
            "timestamp": None,
            "components": {},
            "plugins": {},
            "system_info": {
                "initialized": self._initialized,
                "plugins_initialized": self._plugins_initialized,
                "active_agents": len(self._active_agents),
                "active_workspaces": len(self._active_workspaces),
            },
        }

        try:
            from datetime import datetime

            health_status["timestamp"] = datetime.utcnow().isoformat()

            # Check plugin health
            if self._plugins_initialized:
                plugin_health = await self.plugin_registry.health_check_all_plugins()
                health_status["plugins"] = plugin_health

                # Determine overall status based on plugin health
                unhealthy_plugins = [
                    pid
                    for pid, status in plugin_health.items()
                    if status in ["unhealthy", "unknown"]
                ]

                if unhealthy_plugins:
                    health_status["overall_status"] = "degraded"
                    if len(unhealthy_plugins) > len(plugin_health) // 2:
                        health_status["overall_status"] = "unhealthy"
            else:
                health_status["overall_status"] = "unhealthy"
                health_status["plugins"] = {"error": "Plugins not initialized"}

            # Add component-specific health checks here as they are
            # implemented
            # health_status["components"]["database"] = await
            # self._check_database_health()
            # health_status["components"]["redis"] = await self._check_redis_health()

        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_status["overall_status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information

        Returns:
            Dictionary containing system information
        """
        return {
            "app_name": self.settings.app_name,
            "app_version": self.settings.app_version,
            "environment": self.settings.environment,
            "debug_mode": self.settings.debug,
            "initialized": self._initialized,
            "plugins_initialized": self._plugins_initialized,
            "plugin_info": self.plugin_registry.get_plugin_info(),
            "active_agents": len(self._active_agents),
            "active_workspaces": len(self._active_workspaces),
            "config_dir": str(self.config_manager.config_dir),
        }

    async def reload_configuration(self) -> bool:
        """Reload configuration from files

        Returns:
            True if reload successful, False otherwise
        """
        try:
            logger.info("Reloading configuration...")

            # Reload settings
            old_settings = self._settings
            self._settings = self.config_manager.get_settings(reload=True)

            # TODO: Apply configuration changes to running components
            # This may require restarting some plugins or updating their configurations

            logger.info("Configuration reloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            # Restore old settings if reload failed
            if old_settings:
                self._settings = old_settings
            return False

    @asynccontextmanager
    async def managed_context(self, plugin_paths: Optional[List[Path]] = None):
        """Context manager for automatic initialization and cleanup

        Args:
            plugin_paths: Optional list of paths to discover plugins from
        """
        try:
            await self.initialize(plugin_paths)
            yield self
        finally:
            await self.cleanup()

    async def _create_configured_plugins(self):
        """Create plugin instances from configuration"""
        plugin_configs = self.settings.plugin_configs

        for plugin_name, config in plugin_configs.items():
            if not config or not isinstance(config, dict):
                logger.warning(f"Invalid configuration for plugin {plugin_name}")
                continue

            plugin_type_str = config.get("type")
            if not plugin_type_str:
                logger.warning(f"Plugin {plugin_name} missing type specification")
                continue

            try:
                plugin_type = PluginType(plugin_type_str)

                # Create plugin instance (but don't initialize yet - that happens
                # in initialize_all_plugins)
                self.plugin_registry.create_plugin_instance(
                    plugin_type, plugin_name, config
                )
                logger.info(
                    f"Created configured plugin: {plugin_type_str}.{plugin_name}"
                )

            except ValueError:
                logger.error(
                    f"Unknown plugin type '{plugin_type_str}' for plugin {plugin_name}"
                )
            except Exception as e:
                logger.error(f"Failed to create configured plugin {plugin_name}: {e}")

    async def _initial_health_check(self):
        """Perform initial health check after initialization"""
        health_status = await self.health_check()

        if health_status["overall_status"] == "unhealthy":
            logger.error("System health check failed after initialization")
            raise AgentContextError("System is unhealthy after initialization")
        elif health_status["overall_status"] == "degraded":
            logger.warning("System health is degraded after initialization")
        else:
            logger.info("System health check passed")

    async def _cleanup_active_resources(self):
        """Cleanup active agents and workspaces"""
        # TODO: Implement cleanup of active agents and workspaces
        # This will be implemented when we add agent and workspace management

        cleanup_tasks = []

        # Cleanup active agents
        for agent_id in list(self._active_agents.keys()):
            # cleanup_tasks.append(self._cleanup_agent(agent_id))
            pass

        # Cleanup active workspaces
        for workspace_id in list(self._active_workspaces.keys()):
            # cleanup_tasks.append(self._cleanup_workspace(workspace_id))
            pass

        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to cleanup resource {i}: {result}")

        self._active_agents.clear()
        self._active_workspaces.clear()
