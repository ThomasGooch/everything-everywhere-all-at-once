"""Unit tests for AgentContext"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from core import AgentContext, PluginType


class TestAgentContext:
    """Test AgentContext functionality"""
    
    def test_agent_context_initialization(self):
        """Test AgentContext basic initialization"""
        agent_context = AgentContext()
        
        assert agent_context.config_manager is not None
        assert agent_context.plugin_registry is not None
        assert not agent_context.is_initialized
    
    def test_agent_context_with_custom_config_dir(self, tmp_path):
        """Test AgentContext with custom config directory"""
        config_dir = tmp_path / "custom_config"
        config_dir.mkdir()
        
        agent_context = AgentContext(config_dir)
        
        assert agent_context.config_manager.config_dir == config_dir
    
    @pytest.mark.asyncio
    async def test_agent_context_initialization_success(self, tmp_path):
        """Test successful AgentContext initialization"""
        # Create test config files
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        base_config = config_dir / "base.yaml"
        base_config.write_text("""
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
""")
        
        dev_config = config_dir / "development.yaml"
        dev_config.write_text("debug: true")
        
        agent_context = AgentContext(config_dir)
        
        # Mock plugin initialization to avoid external dependencies
        with patch.object(agent_context.plugin_registry, 'initialize_all_plugins', 
                         return_value={}):
            success = await agent_context.initialize()
            
            assert success
            assert agent_context.is_initialized
            assert agent_context.settings.app_name == "Test App"
            assert agent_context.settings.debug is True
    
    @pytest.mark.asyncio
    async def test_agent_context_cleanup(self, tmp_path):
        """Test AgentContext cleanup"""
        config_dir = tmp_path / "config" 
        config_dir.mkdir()
        
        base_config = config_dir / "base.yaml"
        base_config.write_text("""
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
""")
        
        agent_context = AgentContext(config_dir)
        
        # Initialize first
        with patch.object(agent_context.plugin_registry, 'initialize_all_plugins',
                         return_value={}):
            await agent_context.initialize()
        
        # Now test cleanup
        with patch.object(agent_context.plugin_registry, 'cleanup_all_plugins',
                         return_value={}):
            success = await agent_context.cleanup()
            
            assert success
            assert not agent_context.is_initialized
    
    @pytest.mark.asyncio
    async def test_health_check(self, tmp_path):
        """Test health check functionality"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        base_config = config_dir / "base.yaml"
        base_config.write_text("""
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
""")
        
        agent_context = AgentContext(config_dir)
        
        with patch.object(agent_context.plugin_registry, 'initialize_all_plugins',
                         return_value={}):
            with patch.object(agent_context.plugin_registry, 'health_check_all_plugins',
                             return_value={"test_plugin": "healthy"}):
                await agent_context.initialize()
                
                health_status = await agent_context.health_check()
                
                assert health_status["overall_status"] in ["healthy", "degraded"]
                assert "timestamp" in health_status
                assert "plugins" in health_status
                assert "system_info" in health_status
    
    def test_get_system_info(self, tmp_path):
        """Test system info retrieval"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Create a minimal base config for testing
        base_config = config_dir / "base.yaml"
        base_config.write_text("""
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
""")
        
        agent_context = AgentContext(config_dir)
        
        system_info = agent_context.get_system_info()
        
        assert "initialized" in system_info
        assert "plugins_initialized" in system_info
        assert "plugin_info" in system_info
        assert "config_dir" in system_info
    
    @pytest.mark.asyncio
    async def test_managed_context(self, tmp_path):
        """Test managed context functionality"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        base_config = config_dir / "base.yaml"
        base_config.write_text("""
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
""")
        
        agent_context = AgentContext(config_dir)
        
        with patch.object(agent_context.plugin_registry, 'initialize_all_plugins',
                         return_value={}):
            with patch.object(agent_context.plugin_registry, 'cleanup_all_plugins',
                             return_value={}):
                
                async with agent_context.managed_context() as ctx:
                    assert ctx.is_initialized
                    assert ctx is agent_context
                
                # After context exit, should be cleaned up
                assert not agent_context.is_initialized