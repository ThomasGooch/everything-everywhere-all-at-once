"""Tests for plugin registry module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.plugin_registry import PluginRegistry
from core.plugin_interface import BasePlugin, PluginType, PluginError, PluginValidationError, PluginStatus


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""
    
    def __init__(self, config):
        self._plugin_type = PluginType.TASK_MANAGEMENT
        self._plugin_name = "mock_plugin"
        super().__init__(config)
    
    def get_plugin_type(self) -> PluginType:
        return self._plugin_type
    
    def get_plugin_name(self) -> str:
        return self._plugin_name
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def validate_config(self) -> bool:
        return True
    
    async def initialize(self) -> bool:
        return True
    
    async def cleanup(self) -> bool:
        return True
    
    async def health_check(self) -> PluginStatus:
        return PluginStatus.HEALTHY


class InvalidPlugin:
    """Plugin that doesn't inherit from BasePlugin."""
    pass


class TestPluginRegistry:
    """Test suite for PluginRegistry."""
    
    def setup_method(self):
        """Setup test environment."""
        self.registry = PluginRegistry()
    
    def test_init(self):
        """Test PluginRegistry initialization."""
        registry = PluginRegistry("custom_plugins")
        assert registry.plugins_dir == Path("custom_plugins")
        assert len(registry._plugins) == len(PluginType)
        assert registry._instances == {}
        assert registry.registered_tools == {}
    
    def test_register_plugin_success(self):
        """Test successful plugin registration."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT, 
            "mock_plugin", 
            MockPlugin
        )
        
        plugin_class = self.registry.get_plugin_class(
            PluginType.TASK_MANAGEMENT, 
            "mock_plugin"
        )
        assert plugin_class == MockPlugin
    
    def test_register_plugin_invalid_class(self):
        """Test registering invalid plugin class."""
        with pytest.raises(PluginValidationError):
            self.registry.register_plugin(
                PluginType.TASK_MANAGEMENT,
                "invalid",
                InvalidPlugin
            )
    
    def test_register_plugin_overwrite_warning(self, caplog):
        """Test plugin overwrite warning."""
        # Register first time
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin", 
            MockPlugin
        )
        
        # Register again - should warn
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        assert "already registered, overwriting" in caplog.text
    
    def test_get_plugin_class_not_found(self):
        """Test getting non-existent plugin class."""
        plugin_class = self.registry.get_plugin_class(
            PluginType.TASK_MANAGEMENT,
            "nonexistent"
        )
        assert plugin_class is None
    
    def test_create_plugin_instance_success(self):
        """Test successful plugin instance creation."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {"test": "config"}
        )
        
        assert isinstance(instance, MockPlugin)
        assert instance.config == {"test": "config"}
        
        # Check instance is stored
        stored_instance = self.registry.get_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin"
        )
        assert stored_instance is instance
    
    def test_create_plugin_instance_not_found(self):
        """Test creating instance of non-existent plugin."""
        with pytest.raises(PluginError):
            self.registry.create_plugin_instance(
                PluginType.TASK_MANAGEMENT,
                "nonexistent",
                {}
            )
    
    def test_create_plugin_instance_invalid_config(self):
        """Test creating instance with invalid config."""
        class InvalidConfigPlugin(MockPlugin):
            def get_version(self) -> str:
                return "1.0.0"
            
            def validate_config(self) -> bool:
                return False
        
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "invalid_config",
            InvalidConfigPlugin
        )
        
        with pytest.raises(PluginError):
            self.registry.create_plugin_instance(
                PluginType.TASK_MANAGEMENT,
                "invalid_config",
                {}
            )
    
    def test_get_plugin_instance_by_name(self):
        """Test getting plugin instance by name."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {}
        )
        
        # Test by short name
        found_instance = self.registry.get_plugin_instance_by_name("mock_plugin")
        assert found_instance is instance
        
        # Test by full plugin ID
        found_instance = self.registry.get_plugin_instance_by_name("task_management.mock_plugin")
        assert found_instance is instance
        
        # Test not found
        found_instance = self.registry.get_plugin_instance_by_name("nonexistent")
        assert found_instance is None
    
    def test_list_plugins(self):
        """Test listing plugins."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        # List all plugins
        all_plugins = self.registry.list_plugins()
        assert "task_management" in all_plugins
        assert "mock_plugin" in all_plugins["task_management"]
        
        # List specific type
        task_plugins = self.registry.list_plugins(PluginType.TASK_MANAGEMENT)
        assert task_plugins == {"task_management": ["mock_plugin"]}
    
    @pytest.mark.asyncio
    async def test_initialize_all_plugins(self):
        """Test initializing all plugin instances."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {}
        )
        
        results = await self.registry.initialize_all_plugins()
        assert results["task_management.mock_plugin"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_all_plugins(self):
        """Test cleaning up all plugin instances."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {}
        )
        
        results = await self.registry.cleanup_all_plugins()
        assert results["task_management.mock_plugin"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_all_plugins(self):
        """Test health check for all plugin instances."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {}
        )
        
        results = await self.registry.health_check_all_plugins()
        assert results["task_management.mock_plugin"] == "healthy"
    
    def test_get_plugin_info(self):
        """Test getting plugin information."""
        self.registry.register_plugin(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            MockPlugin
        )
        
        instance = self.registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT,
            "mock_plugin",
            {}
        )
        
        info = self.registry.get_plugin_info()
        assert info["total_registered"] == 1
        assert info["total_instances"] == 1
        assert "task_management" in info["plugins_by_type"]
        assert info["plugins_by_type"]["task_management"]["registered_count"] == 1
    
    def test_discover_plugins_directory_not_exist(self):
        """Test plugin discovery with non-existent directory."""
        registry = PluginRegistry("nonexistent")
        plugins = registry.discover_plugins()
        assert plugins == []
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_discover_plugins_success(self, mock_iterdir, mock_is_dir, mock_exists):
        """Test successful plugin discovery."""
        # Mock directory structure
        mock_exists.return_value = True
        
        mock_plugin_dir = MagicMock()
        mock_plugin_dir.is_dir.return_value = True
        mock_plugin_dir.name = "test_plugin"
        
        mock_tools_file = MagicMock()
        mock_tools_file.exists.return_value = True
        
        # Setup the directory iteration
        mock_iterdir.return_value = [mock_plugin_dir]
        mock_plugin_dir.__truediv__ = lambda self, x: mock_tools_file
        
        plugins = self.registry.discover_plugins()
        assert "test_plugin" in plugins
    
    def test_execute_tool_not_found(self):
        """Test executing non-existent tool."""
        with pytest.raises(ValueError):
            self.registry.execute_tool("nonexistent_tool")
    
    def test_execute_tool_success(self):
        """Test successful tool execution."""
        mock_tool = Mock(return_value="result")
        self.registry.registered_tools["test_tool"] = mock_tool
        
        result = self.registry.execute_tool("test_tool", arg1="value1")
        assert result == "result"
        mock_tool.assert_called_once_with(arg1="value1")
    
    def test_get_available_tools(self):
        """Test getting available tools list."""
        self.registry.registered_tools["tool1"] = Mock()
        self.registry.registered_tools["tool2"] = Mock()
        
        tools = self.registry.get_available_tools()
        assert sorted(tools) == ["tool1", "tool2"]