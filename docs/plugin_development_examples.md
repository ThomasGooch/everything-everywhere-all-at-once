# Plugin Development Examples

> **Real-world examples of implementing production-ready plugins**

## Current Plugin Implementations

### Enhanced Jira Plugin Example

```python
"""
Enhanced Jira plugin implementation with circuit breaker, retry logic, and comprehensive error handling
"""

import asyncio
import base64
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession

from core.circuit_breaker import CircuitBreakerConfig, circuit_breaker_manager
from core.plugin_interface import (
    PluginResult,
    PluginStatus,
    PluginType,
    TaskManagementPlugin,
)
from core.retry_mechanism import RateLimiter, RetryConfig, with_retry

logger = logging.getLogger(__name__)

class JiraPlugin(TaskManagementPlugin):
    """Enhanced Jira integration with advanced features"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._base_url = ""
        self._auth_header = ""

        # Initialize rate limiter and retry configuration
        self._rate_limiter = RateLimiter(max_requests_per_second=2.0)  # Conservative for Jira
        
        # Initialize circuit breaker
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5, 
            recovery_timeout=60.0, 
            success_threshold=2
        )
        self._circuit_breaker = circuit_breaker_manager.get_circuit_breaker(
            f"jira_plugin_{id(self)}", circuit_breaker_config
        )

    def get_plugin_type(self) -> PluginType:
        return PluginType.TASK_MANAGEMENT

    def get_plugin_name(self) -> str:
        return "jira"

    def get_version(self) -> str:
        return "2.0.0"

    def get_required_config_keys(self) -> List[str]:
        return ["connection.url", "connection.email", "connection.api_token"]

    def get_optional_config_keys(self) -> List[str]:
        return [
            "options.timeout",
            "options.retry_attempts", 
            "options.custom_fields",
            "mappings"
        ]

    def validate_config(self) -> bool:
        """Validate plugin configuration with detailed error reporting"""
        connection = self.config.get("connection", {})
        
        required_fields = ["url", "email", "api_token"]
        for field in required_fields:
            if not connection.get(field):
                logger.error(f"Missing required Jira config: connection.{field}")
                return False
                
        # Validate URL format
        url = connection["url"]
        if not url.startswith(("http://", "https://")):
            logger.error("Jira URL must start with http:// or https://")
            return False
            
        return True

    async def initialize(self) -> None:
        """Initialize Jira connection with authentication"""
        if self._is_initialized:
            return
            
        connection = self.config["connection"]
        self._base_url = connection["url"].rstrip("/")
        
        # Create base64 encoded auth header
        auth_string = f"{connection['email']}:{connection['api_token']}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        self._auth_header = f"Basic {auth_b64}"
        
        # Create HTTP session with timeout
        timeout = aiohttp.ClientTimeout(
            total=self.config.get("options", {}).get("timeout", 30)
        )
        self._session = ClientSession(timeout=timeout)
        
        # Test connection
        await self._test_connection()
        
        self._is_initialized = True
        self._connection_established = True
        logger.info("Jira plugin initialized successfully")

    async def get_task(self, task_id: str) -> PluginResult:
        """Enhanced task retrieval with circuit breaker and error handling"""
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        @with_retry(self._retry_config)
        async def _get_task_with_retry():
            url = f"{self._base_url}/rest/api/2/issue/{task_id}"
            
            async def _http_call():
                async with self._session.get(url, headers={"Authorization": self._auth_header}) as response:
                    return (response, await response.text() if response.status != 200 else await response.json())

            response, data = await self._circuit_breaker.call(_http_call)

            if response.status == 404:
                raise ValueError(f"Task {task_id} not found")
            elif response.status >= 500 or response.status == 429:
                # Retry server errors and rate limiting
                error = aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=str(data),
                )
                raise error
            elif response.status != 200:
                raise ValueError(f"API error {response.status}: {data}")

            return data  # This is the JSON data

        try:
            issue_data = await _get_task_with_retry()
            
            # Map Jira fields to standard format
            task_data = self._map_issue_to_standard_format(issue_data)
            
            return PluginResult(
                success=True, 
                data=task_data, 
                metadata={"raw_issue": issue_data}
            )

        except Exception as e:
            logger.error(f"Error retrieving task {task_id}: {e}")
            return PluginResult(
                success=False, 
                error=f"Failed to get task {task_id}: {e}"
            )

    def _map_issue_to_standard_format(self, issue_data: Dict) -> Dict:
        """Map Jira issue to standard format with custom fields support"""
        fields = issue_data["fields"]
        custom_fields = self.config.get("options", {}).get("custom_fields", {})
        
        # Extract custom fields if configured
        story_points = None
        epic_link = None
        team = None
        
        if "story_points" in custom_fields:
            story_points = fields.get(custom_fields["story_points"])
        if "epic_link" in custom_fields:
            epic_link = fields.get(custom_fields["epic_link"])
        if "team" in custom_fields:
            team = fields.get(custom_fields["team"])
        
        return {
            "task_id": issue_data["key"],
            "title": fields["summary"],
            "description": fields.get("description", ""),
            "status": fields["status"]["name"],
            "assignee": fields["assignee"]["displayName"] if fields.get("assignee") else None,
            "priority": fields["priority"]["name"] if fields.get("priority") else None,
            "story_points": story_points,
            "epic_link": epic_link,
            "team": team,
            "created": fields["created"],
            "updated": fields["updated"],
        }

    async def health_check(self) -> PluginStatus:
        """Comprehensive health check with external API validation"""
        if not self._is_initialized or not self._session:
            return PluginStatus.UNHEALTHY

        try:
            url = f"{self._base_url}/rest/api/2/serverInfo"
            async with self._session.get(url, headers={"Authorization": self._auth_header}) as response:
                if response.status == 200:
                    return PluginStatus.HEALTHY
                else:
                    return PluginStatus.DEGRADED
        except Exception:
            return PluginStatus.UNHEALTHY

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self._session:
            await self._session.close()
            self._session = None
        self._is_initialized = False
        self._connection_established = False
        logger.info("Jira plugin cleaned up")
```

## Testing Production Plugins

### Comprehensive Test Suite Example

```python
"""
Comprehensive test suite for Jira plugin with mocking and integration tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.jira_plugin import JiraPlugin
from core.plugin_interface import PluginStatus, PluginResult

class AsyncContextManagerMock:
    """Mock async context manager for testing"""
    
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class TestJiraPlugin:
    """Comprehensive test suite for Jira plugin"""

    @pytest.fixture
    def jira_config(self):
        """Standard Jira configuration for testing"""
        return {
            "connection": {
                "url": "https://test-company.atlassian.net",
                "email": "test@company.com",
                "api_token": "test_token_123",
            },
            "options": {
                "timeout": 30,
                "retry_attempts": 3,
                "custom_fields": {
                    "story_points": "customfield_10001",
                    "epic_link": "customfield_10002", 
                    "team": "customfield_10003",
                },
            },
            "provider": "jira",
        }

    @pytest.fixture
    def jira_plugin(self, jira_config):
        """Create JiraPlugin instance for testing"""
        return JiraPlugin(jira_config)

    def test_plugin_metadata(self, jira_plugin):
        """Test plugin returns correct metadata"""
        assert jira_plugin.get_plugin_name() == "jira"
        assert jira_plugin.get_version() == "2.0.0"
        assert jira_plugin.get_plugin_type() == PluginType.TASK_MANAGEMENT

    def test_config_validation_success(self, jira_plugin):
        """Test successful configuration validation"""
        assert jira_plugin.validate_config() is True

    def test_config_validation_missing_url(self):
        """Test config validation fails with missing URL"""
        invalid_config = {
            "connection": {
                "email": "test@company.com",
                "api_token": "token123",
            }
        }
        plugin = JiraPlugin(invalid_config)
        assert plugin.validate_config() is False

    @pytest.mark.asyncio
    async def test_get_task_success(self, jira_config):
        """Test successful task retrieval with enhanced features"""
        plugin = JiraPlugin(jira_config)
        plugin._is_initialized = True
        plugin._connection_established = True
        plugin._base_url = "https://test-company.atlassian.net"
        plugin._auth_header = "Basic test_auth"

        # Create mock session
        mock_session = MagicMock()
        plugin._session = mock_session

        # Mock successful response with custom fields
        mock_response = MagicMock()
        mock_response.status = 200
        mock_task_data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test task",
                "description": "Test description", 
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "John Doe"},
                "priority": {"name": "High"},
                "created": "2024-01-15T10:00:00.000Z",
                "updated": "2024-01-15T12:00:00.000Z",
                "customfield_10001": 8,  # story_points
                "customfield_10003": "Alpha Team",  # team
            },
        }
        mock_response.json = AsyncMock(return_value=mock_task_data)
        mock_session.get.return_value = AsyncContextManagerMock(mock_response)

        result = await plugin.get_task("TEST-123")

        assert result.success is True
        assert result.data["task_id"] == "TEST-123"
        assert result.data["title"] == "Test task"
        assert result.data["story_points"] == 8
        assert result.data["team"] == "Alpha Team"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, jira_config):
        """Test health check when service is healthy"""
        plugin = JiraPlugin(jira_config)
        plugin._is_initialized = True
        plugin._connection_established = True
        plugin._base_url = "https://test-company.atlassian.net"
        plugin._auth_header = "Basic test_auth"

        # Create mock session
        mock_session = MagicMock()
        plugin._session = mock_session

        # Mock healthy response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_session.get.return_value = AsyncContextManagerMock(mock_response)

        status = await plugin.health_check()
        assert status == PluginStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, jira_config):
        """Test circuit breaker integration with plugin"""
        plugin = JiraPlugin(jira_config)
        plugin._is_initialized = True
        plugin._connection_established = True
        plugin._base_url = "https://test-company.atlassian.net"
        plugin._auth_header = "Basic test_auth"

        # Mock session that always returns server error
        mock_session = MagicMock()
        plugin._session = mock_session

        mock_response = MagicMock()
        mock_response.status = 503
        mock_response.text = AsyncMock(return_value="Service Unavailable")
        mock_response.request_info = MagicMock()
        mock_response.history = []
        mock_session.get.return_value = AsyncContextManagerMock(mock_response)

        # Multiple failures should eventually trigger circuit breaker
        for i in range(6):  # Exceed failure threshold
            result = await plugin.get_task("TEST-123")
            assert result.success is False

        # Verify circuit breaker state (in production implementation)
        # This would require accessing circuit breaker state
```

## Plugin Development Best Practices

### 1. Error Handling Patterns

```python
# Always return PluginResult for consistent error handling
async def some_plugin_method(self) -> PluginResult:
    try:
        # Plugin logic here
        result = await external_api_call()
        return PluginResult(success=True, data=result)
    except SpecificAPIError as e:
        logger.error(f"Specific API error: {e}")
        return PluginResult(success=False, error=f"API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return PluginResult(success=False, error=f"Unexpected error: {e}")
```

### 2. Circuit Breaker Integration

```python
# Use circuit breakers for external API calls
async def _make_api_call(self):
    async def _http_call():
        async with self._session.get(url) as response:
            if response.status >= 500:
                raise aiohttp.ClientResponseError(...)
            return await response.json()
    
    return await self._circuit_breaker.call(_http_call)
```

### 3. Rate Limiting

```python
# Always respect rate limits
async def api_method(self):
    await self._rate_limiter.acquire()  # Wait for rate limit
    # Make API call
```

### 4. Configuration Validation

```python
def validate_config(self) -> bool:
    """Comprehensive configuration validation"""
    # Check required fields
    required = self.get_required_config_keys()
    for key in required:
        if not self._get_nested_config(key):
            logger.error(f"Missing required config: {key}")
            return False
    
    # Validate URL formats, tokens, etc.
    if "url" in self.config.get("connection", {}):
        url = self.config["connection"]["url"]
        if not url.startswith(("http://", "https://")):
            logger.error("URL must start with http:// or https://")
            return False
    
    return True
```

### 5. Testing Patterns

```python
# Use fixtures for consistent test setup
@pytest.fixture
def plugin_config():
    return {"connection": {"url": "...", "token": "..."}}

@pytest.fixture  
def plugin(plugin_config):
    return MyPlugin(plugin_config)

# Mock external dependencies
@pytest.mark.asyncio
async def test_method_success(plugin):
    with patch('external_api.call') as mock_call:
        mock_call.return_value = {"success": True}
        result = await plugin.method()
        assert result.success is True
```

## Quality Assurance

### Running Plugin Tests

```bash
# Run all plugin tests
poetry run pytest tests/unit/test_*plugin*.py -v

# Run specific plugin tests
poetry run pytest tests/unit/test_jira_plugin.py -v

# Run with coverage
poetry run pytest tests/unit/test_jira_plugin.py --cov=plugins.jira_plugin

# Run integration tests (requires external services)
poetry run pytest tests/integration/test_enhanced_plugins_integration.py -m integration
```

### Code Quality Checks

```bash
# Format code
poetry run black plugins/your_plugin.py

# Check formatting
poetry run black plugins/your_plugin.py --check

# Lint code
poetry run flake8 plugins/your_plugin.py

# Type checking
poetry run mypy plugins/your_plugin.py

# Security scan
poetry run bandit plugins/your_plugin.py
```

This comprehensive guide provides real examples from our production plugin implementations, showing how to build robust, testable plugins with proper error handling, circuit breakers, and comprehensive testing.