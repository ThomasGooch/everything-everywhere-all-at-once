"""Configuration management system with environment-based overrides"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration"""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum connection overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")


class RedisConfig(BaseModel):
    """Redis configuration"""

    url: str = Field(..., description="Redis connection URL")
    max_connections: int = Field(default=20, description="Maximum connections")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")


class AIConfig(BaseModel):
    """AI provider configuration"""

    provider: str = Field(..., description="AI provider name")
    api_key: str = Field(..., description="API key")
    model: str = Field(default="claude-3-sonnet-20240229", description="Model name")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    timeout: int = Field(default=60, description="Request timeout in seconds")


class SecurityConfig(BaseModel):
    """Security configuration"""

    jwt_secret: str = Field(..., description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiry_hours: int = Field(default=24, description="JWT token expiry in hours")
    encryption_key: Optional[str] = Field(
        default=None, description="Encryption key for sensitive data"
    )
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(
        default=30, description="Account lockout duration"
    )


class WorkspaceConfig(BaseModel):
    """Workspace configuration"""

    base_path: str = Field(
        default="/tmp/ai-orchestrator-workspaces",
        description="Base workspace directory",
    )
    max_workspaces: int = Field(default=50, description="Maximum concurrent workspaces")
    cleanup_after_hours: int = Field(default=24, description="Auto-cleanup after hours")
    max_disk_usage_gb: int = Field(default=100, description="Maximum disk usage in GB")


class MonitoringConfig(BaseModel):
    """Monitoring and logging configuration"""

    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    health_check_interval: int = Field(
        default=60, description="Health check interval in seconds"
    )


class Settings(BaseSettings):
    """Main application settings"""

    # Basic application settings
    app_name: str = Field(
        default="AI Development Orchestrator", description="Application name"
    )
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Component configurations
    database: DatabaseConfig
    redis: RedisConfig
    ai: AIConfig
    security: SecurityConfig
    workspace: WorkspaceConfig
    monitoring: MonitoringConfig

    # Plugin configurations (loaded from separate files)
    plugin_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    @field_validator("database", mode="before")
    @classmethod
    def validate_database_config(cls, v):
        """Validate database configuration"""
        if isinstance(v, str):
            return {"url": v}
        return v

    @field_validator("redis", mode="before")
    @classmethod
    def validate_redis_config(cls, v):
        """Validate Redis configuration"""
        if isinstance(v, str):
            return {"url": v}
        return v


class ConfigManager:
    """Configuration manager with YAML loading and environment overrides"""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir or Path("config")
        self._settings: Optional[Settings] = None
        self._config_cache: Dict[str, Any] = {}

    def load_yaml_config(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from YAML file

        Args:
            config_file: Path to YAML configuration file

        Returns:
            Configuration dictionary
        """
        if not config_file.exists():
            logger.warning(f"Configuration file {config_file} not found")
            return {}

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            logger.info(f"Loaded configuration from {config_file}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {config_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration file {config_file}: {e}")
            raise

    def load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Environment-specific configuration
        """
        # Load base configuration
        base_config_file = self.config_dir / "base.yaml"
        base_config = self.load_yaml_config(base_config_file)

        # Load environment-specific overrides
        env_config_file = self.config_dir / f"{environment}.yaml"
        env_config = self.load_yaml_config(env_config_file)

        # Merge configurations (environment overrides base)
        merged_config = self._deep_merge(base_config, env_config)

        return merged_config

    def load_plugin_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load plugin configurations from separate files

        Returns:
            Dictionary mapping plugin names to their configurations
        """
        plugin_configs = {}
        plugin_config_dir = self.config_dir / "plugins"

        if not plugin_config_dir.exists():
            logger.info(f"Plugin config directory {plugin_config_dir} not found")
            return plugin_configs

        # Load all YAML files in the plugins directory
        for config_file in plugin_config_dir.glob("*.yaml"):
            plugin_name = config_file.stem
            try:
                plugin_config = self.load_yaml_config(config_file)
                plugin_configs[plugin_name] = plugin_config
                logger.info(f"Loaded plugin config for {plugin_name}")
            except Exception as e:
                logger.error(f"Failed to load plugin config {config_file}: {e}")

        return plugin_configs

    def get_settings(self, reload: bool = False) -> Settings:
        """Get application settings

        Args:
            reload: Force reload of configuration

        Returns:
            Application settings instance
        """
        if self._settings is None or reload:
            self._settings = self._load_settings()

        return self._settings

    def _load_settings(self) -> Settings:
        """Load settings from configuration files and environment variables

        Returns:
            Settings instance
        """
        # Determine environment
        environment = os.getenv("ENVIRONMENT", "development").lower()

        # Load configuration from files
        config = self.load_environment_config(environment)

        # Load plugin configurations
        plugin_configs = self.load_plugin_configs()
        config["plugin_configs"] = plugin_configs

        # Add environment to config
        config["environment"] = environment

        # Apply environment variable overrides
        config = self._apply_env_overrides(config)

        try:
            settings = Settings(**config)
            logger.info(f"Loaded settings for environment: {environment}")
            return settings
        except Exception as e:
            logger.error(f"Failed to create Settings instance: {e}")
            raise

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration

        Args:
            config: Base configuration

        Returns:
            Configuration with environment overrides applied
        """
        # Environment variables that map to config keys
        env_mappings = {
            "DATABASE_URL": ("database", "url"),
            "REDIS_URL": ("redis", "url"),
            "AI_API_KEY": ("ai", "api_key"),
            "JWT_SECRET": ("security", "jwt_secret"),
            "ENCRYPTION_KEY": ("security", "encryption_key"),
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_config(config, config_path, env_value)

        return config

    def _set_nested_config(self, config: Dict[str, Any], path: tuple, value: str):
        """Set nested configuration value

        Args:
            config: Configuration dictionary
            path: Tuple representing nested path
            value: Value to set
        """
        current = config

        # Navigate to the parent of the target key
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the target value
        current[path[-1]] = value

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dictionary
        """
        settings = self.get_settings()
        return settings.plugin_configs.get(plugin_name, {})
