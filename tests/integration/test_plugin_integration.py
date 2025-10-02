"""Integration tests for plugin loading and AgentContext integration"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.agent_context import AgentContext
from core.plugin_interface import PluginType
from plugins.jira_plugin import JiraPlugin


class TestPluginIntegration:
    """Test plugin integration with AgentContext"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory with plugin configs"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Base config
        base_config = config_dir / "base.yaml"
        base_config.write_text(
            """
app_name: "Test App"
database:
  url: "sqlite:///test.db"
redis:
  url: "redis://localhost:6379/0"
ai:
  provider: "test"
  api_key: "test_key"
security:
  jwt_secret: "test_secret"
workspace:
  base_path: "/tmp/test"
monitoring:
  log_level: "INFO"
"""
        )

        # Plugin configs
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir()

        jira_config = plugins_dir / "jira.yaml"
        jira_config.write_text(
            """
type: "task_management"
provider: "jira"
connection:
  url: "https://test-company.atlassian.net"
  email: "test@company.com"
  api_token: "test_token_123"
mappings:
  task_id: "key"
  title: "fields.summary"
options:
  timeout: 30
  retry_attempts: 3
"""
        )

        return config_dir

    def test_jira_plugin_direct_instantiation(self):
        """Test direct plugin instantiation and configuration"""
        config = {
            "type": "task_management",
            "provider": "jira",
            "connection": {
                "url": "https://test-company.atlassian.net",
                "email": "test@company.com",
                "api_token": "test_token",
            },
            "options": {"timeout": 30},
        }

        plugin = JiraPlugin(config)

        assert plugin.get_plugin_type() == PluginType.TASK_MANAGEMENT
        assert plugin.get_plugin_name() == "jira"
        assert plugin.get_version() == "1.0.0"
        assert plugin.validate_config() is True

    def test_plugin_registry_registration(self):
        """Test plugin can be registered with plugin registry"""
        from core.plugin_registry import PluginRegistry

        registry = PluginRegistry()
        registry.register_plugin(PluginType.TASK_MANAGEMENT, "jira", JiraPlugin)

        # Verify plugin is registered
        plugins = registry.list_plugins()
        assert "task_management" in plugins
        assert "jira" in plugins["task_management"]

        # Verify we can get the plugin class
        plugin_class = registry.get_plugin_class(PluginType.TASK_MANAGEMENT, "jira")
        assert plugin_class == JiraPlugin

    def test_plugin_instance_creation(self):
        """Test plugin instance creation through registry"""
        from core.plugin_registry import PluginRegistry

        config = {
            "connection": {
                "url": "https://test-company.atlassian.net",
                "email": "test@company.com",
                "api_token": "test_token",
            }
        }

        registry = PluginRegistry()
        registry.register_plugin(PluginType.TASK_MANAGEMENT, "jira", JiraPlugin)

        plugin_instance = registry.create_plugin_instance(
            PluginType.TASK_MANAGEMENT, "jira", config
        )

        assert isinstance(plugin_instance, JiraPlugin)
        assert plugin_instance.config == config

    @pytest.mark.asyncio
    async def test_agent_context_plugin_loading(self, temp_config_dir):
        """Test plugin loading through AgentContext"""
        agent_context = AgentContext(temp_config_dir)

        # Mock plugin initialization to avoid external dependencies
        with patch.object(
            agent_context.plugin_registry,
            "initialize_all_plugins",
            return_value={"task_management.jira": True},
        ):
            # Register the plugin manually since we don't have discovery
            agent_context.plugin_registry.register_plugin(
                PluginType.TASK_MANAGEMENT, "jira", JiraPlugin
            )

            success = await agent_context.initialize(skip_health_check=True)

            assert success is True
            assert agent_context.is_initialized

            # Verify plugin configuration was loaded
            plugin_configs = agent_context.settings.plugin_configs
            assert "jira" in plugin_configs
            assert plugin_configs["jira"]["type"] == "task_management"

            await agent_context.cleanup()

    @pytest.mark.asyncio
    async def test_plugin_health_check_integration(self, temp_config_dir):
        """Test plugin health check through AgentContext"""
        agent_context = AgentContext(temp_config_dir)

        # Register and create plugin instance
        agent_context.plugin_registry.register_plugin(
            PluginType.TASK_MANAGEMENT, "jira", JiraPlugin
        )

        plugin_config = {
            "connection": {
                "url": "https://test-company.atlassian.net",
                "email": "test@company.com",
                "api_token": "test_token",
            }
        }

        with patch.object(
            agent_context.plugin_registry,
            "initialize_all_plugins",
            return_value={"task_management.jira": True},
        ):
            with patch.object(
                agent_context.plugin_registry,
                "health_check_all_plugins",
                return_value={"task_management.jira": "healthy"},
            ):
                plugin_instance = agent_context.plugin_registry.create_plugin_instance(
                    PluginType.TASK_MANAGEMENT, "jira", plugin_config
                )

                await agent_context.initialize()

                health_status = await agent_context.health_check()

                assert health_status["overall_status"] in ["healthy", "degraded"]
                assert "plugins" in health_status
                assert "task_management.jira" in health_status["plugins"]

                await agent_context.cleanup()

    def test_plugin_configuration_validation(self):
        """Test plugin configuration validation"""
        # Valid configuration
        valid_config = {
            "connection": {
                "url": "https://test-company.atlassian.net",
                "email": "test@company.com",
                "api_token": "test_token",
            }
        }

        plugin = JiraPlugin(valid_config)
        assert plugin.validate_config() is True

        # Invalid configuration - missing URL
        invalid_config = {
            "connection": {"email": "test@company.com", "api_token": "test_token"}
        }

        plugin = JiraPlugin(invalid_config)
        with pytest.raises(Exception):  # PluginValidationError
            plugin.validate_config()

    def test_plugin_required_and_optional_keys(self):
        """Test plugin configuration key requirements"""
        plugin = JiraPlugin({})

        required_keys = plugin.get_required_config_keys()
        optional_keys = plugin.get_optional_config_keys()

        # Check required keys
        assert "connection.url" in required_keys
        assert "connection.email" in required_keys
        assert "connection.api_token" in required_keys

        # Check optional keys
        assert "options.timeout" in optional_keys
        assert "options.retry_attempts" in optional_keys
