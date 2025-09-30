# Plugin Development Guide

> **Complete guide to developing custom plugins for the AI Development Automation System**

## Table of Contents

1. [Overview](#overview)
2. [Plugin Architecture](#plugin-architecture)
3. [Getting Started](#getting-started)
4. [Plugin Types](#plugin-types)
5. [Implementation Guide](#implementation-guide)
6. [Configuration Management](#configuration-management)
7. [Testing Plugins](#testing-plugins)
8. [Best Practices](#best-practices)
9. [Publishing Plugins](#publishing-plugins)
10. [Examples](#examples)

---

## Overview

The plugin system is the heart of the AI Development Automation System's flexibility. Plugins allow integration with any external service through standardized interfaces, making the system truly universal.

### Why Plugins?

- **Extensibility**: Support new tools without modifying core code
- **Maintainability**: Each integration is isolated and independently testable
- **Flexibility**: Mix and match any combination of tools
- **Community**: Enable community-contributed integrations

### Plugin Lifecycle

```
Discovery → Loading → Validation → Configuration → Registration → Usage → Cleanup
```

---

## Plugin Architecture

### Base Plugin Structure

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

class BasePlugin(ABC):
    """Base class for all plugins"""
    
    # Plugin metadata
    PLUGIN_NAME: str = ""
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_DESCRIPTION: str = ""
    REQUIRED_CONFIG: list = []
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"plugin.{self.PLUGIN_NAME}")
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Initialize connection to external service"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanup connection resources"""
        pass
        
    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is accessible"""
        pass
        
    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        for required_key in self.REQUIRED_CONFIG:
            if required_key not in self.config:
                self.logger.error(f"Missing required config key: {required_key}")
                return False
        return True
```

### Plugin Registry

```python
class PluginRegistry:
    """Central registry for all plugins"""
    
    def __init__(self):
        self._plugins = {
            'task_management': {},
            'version_control': {},
            'documentation': {},
            'communication': {},
            'ai_provider': {},
            'monitoring': {}
        }
        
    def register_plugin(self, plugin_type: str, name: str, plugin_class):
        """Register a plugin class"""
        if plugin_type not in self._plugins:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
            
        self._plugins[plugin_type][name] = plugin_class
        
    def get_plugin_class(self, plugin_type: str, name: str):
        """Get plugin class by type and name"""
        return self._plugins[plugin_type].get(name)
        
    def list_plugins(self, plugin_type: str = None) -> Dict:
        """List available plugins"""
        if plugin_type:
            return self._plugins.get(plugin_type, {})
        return self._plugins
```

---

## Getting Started

### Development Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/ai-dev-orchestrator
cd ai-dev-orchestrator

# 2. Create development environment
python -m venv plugin-dev-env
source plugin-dev-env/bin/activate

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Install in development mode
pip install -e .
```

### Plugin Directory Structure

```
my_custom_plugin/
├── __init__.py
├── plugin.py                 # Main plugin implementation
├── config.yaml.example       # Configuration template
├── tests/
│   ├── __init__.py
│   ├── test_plugin.py
│   └── conftest.py
├── README.md
└── requirements.txt          # Plugin-specific dependencies
```

### Plugin Template

```python
# my_custom_plugin/plugin.py
from core.plugin_interface import TaskManagementPlugin
from typing import Dict, Any, List
import aiohttp

class MyCustomTaskPlugin(TaskManagementPlugin):
    """Custom task management plugin for MyService"""
    
    PLUGIN_NAME = "mycustom"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Integration with My Custom Task Management Service"
    REQUIRED_CONFIG = ["api_url", "api_key", "project_id"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config["api_url"]
        self.api_key = config["api_key"]
        self.project_id = config["project_id"]
        self.session = None
        
    async def connect(self) -> bool:
        """Initialize HTTP session"""
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            # Test connection
            async with self.session.get(f"{self.api_url}/health") as response:
                self._connected = response.status == 200
                return self._connected
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self._connected = False
            
    def health_check(self) -> bool:
        """Check connection status"""
        return self._connected
        
    # Implement abstract methods...
    async def get_task(self, task_id: str) -> Dict:
        # Implementation here
        pass
```

---

## Plugin Types

### 1. Task Management Plugins

**Purpose**: Integrate with project management systems

**Interface**: `TaskManagementPlugin`

**Required Methods**:
```python
async def get_task(self, task_id: str) -> Dict
async def create_task(self, project: str, task_data: Dict) -> str
async def update_task_status(self, task_id: str, status: str) -> bool
async def add_comment(self, task_id: str, comment: str) -> bool
async def create_epic(self, project: str, epic_data: Dict) -> str
async def get_project_tasks(self, project: str, status: str = None) -> List[Dict]
async def assign_task(self, task_id: str, assignee: str) -> bool
async def get_task_history(self, task_id: str) -> List[Dict]
```

**Standard Data Format**:
```python
{
    "id": "PROJ-123",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system",
    "status": "in_progress",  # todo, in_progress, in_review, done
    "assignee": "john@example.com",
    "priority": "high",  # low, medium, high, critical
    "labels": ["backend", "security"],
    "created": "2024-01-15T10:30:00Z",
    "updated": "2024-01-16T15:45:00Z",
    "due_date": "2024-01-20T23:59:59Z",
    "epic_id": "PROJ-100",
    "story_points": 8,
    "custom_fields": {}
}
```

### 2. Version Control Plugins

**Purpose**: Integrate with code repositories

**Interface**: `VersionControlPlugin`

**Required Methods**:
```python
async def clone_repository(self, repository_url: str, local_path: str) -> bool
async def create_branch(self, repository: str, branch_name: str, base_branch: str = "main") -> bool
async def commit_changes(self, repository: str, message: str, files: List[str]) -> str
async def push_branch(self, repository: str, branch_name: str) -> bool
async def create_pull_request(self, repository: str, pr_data: Dict) -> str
async def get_repository_info(self, repository: str) -> Dict
async def get_file_content(self, repository: str, file_path: str, branch: str = "main") -> str
async def update_file(self, repository: str, file_path: str, content: str, message: str, branch: str) -> bool
```

### 3. Documentation Plugins

**Purpose**: Integrate with documentation platforms

**Interface**: `DocumentationPlugin`

**Required Methods**:
```python
async def create_page(self, space: str, title: str, content: str) -> str
async def update_page(self, page_id: str, content: str) -> bool
async def get_page(self, page_id: str) -> Dict
async def delete_page(self, page_id: str) -> bool
async def search_pages(self, query: str, space: str = None) -> List[Dict]
async def create_space(self, space_data: Dict) -> str
async def get_page_history(self, page_id: str) -> List[Dict]
```

### 4. Communication Plugins

**Purpose**: Integrate with team communication tools

**Interface**: `CommunicationPlugin`

**Required Methods**:
```python
async def send_message(self, channel: str, message: str, thread_id: str = None) -> str
async def send_direct_message(self, user: str, message: str) -> str
async def create_channel(self, channel_data: Dict) -> str
async def get_channel_info(self, channel: str) -> Dict
async def get_user_info(self, user: str) -> Dict
async def upload_file(self, channel: str, file_path: str, comment: str = None) -> bool
```

### 5. AI Provider Plugins

**Purpose**: Integrate with AI services

**Interface**: `AIProviderPlugin`

**Required Methods**:
```python
async def generate_text(self, prompt: str, max_tokens: int = 1000) -> str
async def analyze_code(self, code: str, language: str) -> Dict
async def generate_code(self, requirements: str, context: Dict) -> str
async def estimate_cost(self, prompt: str) -> float
async def get_usage_stats(self) -> Dict
```

---

## Implementation Guide

### Step 1: Choose Your Plugin Type

Identify which interface your plugin should implement based on the service you're integrating.

### Step 2: Implement the Interface

```python
from core.plugin_interface import TaskManagementPlugin
import asyncio
import aiohttp
from typing import Dict, Any, List

class LinearPlugin(TaskManagementPlugin):
    """Linear task management integration"""
    
    PLUGIN_NAME = "linear"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Linear issue tracking integration"
    REQUIRED_CONFIG = ["api_key", "team_id"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.team_id = config["team_id"]
        self.base_url = "https://api.linear.app/graphql"
        self.session = None
        
    async def connect(self) -> bool:
        """Initialize GraphQL client"""
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            # Test connection with team query
            query = """
            query {
                teams(filter: { id: { eq: "%s" } }) {
                    nodes { id name }
                }
            }
            """ % self.team_id
            
            async with self.session.post(
                self.base_url, 
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._connected = len(data.get("data", {}).get("teams", {}).get("nodes", [])) > 0
                    return self._connected
                    
        except Exception as e:
            self.logger.error(f"Linear connection failed: {e}")
            
        return False
        
    async def disconnect(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self._connected = False
            
    def health_check(self) -> bool:
        """Check connection status"""
        return self._connected
        
    async def get_task(self, task_id: str) -> Dict:
        """Get issue from Linear"""
        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                state { name }
                assignee { email }
                priority
                labels { nodes { name } }
                createdAt
                updatedAt
                dueDate
            }
        }
        """
        
        async with self.session.post(
            self.base_url,
            json={"query": query, "variables": {"id": task_id}}
        ) as response:
            data = await response.json()
            issue = data["data"]["issue"]
            
            return {
                "id": issue["identifier"],
                "title": issue["title"],
                "description": issue["description"],
                "status": self._map_status(issue["state"]["name"]),
                "assignee": issue["assignee"]["email"] if issue["assignee"] else None,
                "priority": self._map_priority(issue["priority"]),
                "labels": [label["name"] for label in issue["labels"]["nodes"]],
                "created": issue["createdAt"],
                "updated": issue["updatedAt"],
                "due_date": issue["dueDate"]
            }
            
    async def create_task(self, project: str, task_data: Dict) -> str:
        """Create new issue in Linear"""
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                issue { id identifier }
                success
            }
        }
        """
        
        input_data = {
            "teamId": self.team_id,
            "title": task_data["title"],
            "description": task_data.get("description", ""),
            "priority": self._map_priority_to_linear(task_data.get("priority", "medium"))
        }
        
        if "assignee" in task_data:
            # Look up user ID by email
            user_id = await self._get_user_id_by_email(task_data["assignee"])
            if user_id:
                input_data["assigneeId"] = user_id
                
        async with self.session.post(
            self.base_url,
            json={"query": mutation, "variables": {"input": input_data}}
        ) as response:
            data = await response.json()
            if data["data"]["issueCreate"]["success"]:
                return data["data"]["issueCreate"]["issue"]["identifier"]
            else:
                raise Exception("Failed to create Linear issue")
                
    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Update issue status in Linear"""
        # First get the state ID for the status
        state_id = await self._get_state_id_by_name(self._map_status_to_linear(status))
        if not state_id:
            return False
            
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """
        
        async with self.session.post(
            self.base_url,
            json={
                "query": mutation,
                "variables": {
                    "id": task_id,
                    "input": {"stateId": state_id}
                }
            }
        ) as response:
            data = await response.json()
            return data["data"]["issueUpdate"]["success"]
            
    # Helper methods
    def _map_status(self, linear_status: str) -> str:
        """Map Linear status to standard status"""
        mapping = {
            "Backlog": "todo",
            "Todo": "todo",
            "In Progress": "in_progress",
            "In Review": "in_review", 
            "Done": "done"
        }
        return mapping.get(linear_status, "todo")
        
    def _map_priority(self, linear_priority: int) -> str:
        """Map Linear priority to standard priority"""
        if linear_priority >= 3:
            return "critical"
        elif linear_priority == 2:
            return "high"
        elif linear_priority == 1:
            return "medium"
        else:
            return "low"
            
    # ... implement other required methods
```

### Step 3: Configuration Schema

Create a configuration schema for your plugin:

```yaml
# plugins/linear.config.yaml
provider: "linear"

connection:
  api_key: "${LINEAR_API_KEY}"
  team_id: "${LINEAR_TEAM_ID}"

mappings:
  # Status mappings
  statuses:
    todo: "Backlog"
    in_progress: "In Progress"
    in_review: "In Review"
    done: "Done"
    
  # Priority mappings
  priorities:
    low: 0
    medium: 1
    high: 2
    critical: 3
    
options:
  auto_assign: false
  default_priority: "medium"
  include_labels: true
```

### Step 4: Plugin Registration

Register your plugin with the system:

```python
# plugins/__init__.py
from .linear_plugin import LinearPlugin
from core.plugin_registry import PluginRegistry

# Register the plugin
PluginRegistry.register_plugin("task_management", "linear", LinearPlugin)
```

### Step 5: Error Handling

Implement comprehensive error handling:

```python
from typing import Optional
import logging

class PluginError(Exception):
    """Base plugin error"""
    pass

class ConnectionError(PluginError):
    """Connection-related errors"""
    pass

class ConfigurationError(PluginError):
    """Configuration-related errors"""
    pass

class LinearPlugin(TaskManagementPlugin):
    
    async def get_task(self, task_id: str) -> Dict:
        """Get task with proper error handling"""
        try:
            if not self._connected:
                raise ConnectionError("Plugin not connected")
                
            # Implementation...
            
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error retrieving task {task_id}: {e}")
            raise ConnectionError(f"Failed to retrieve task: {e}")
            
        except KeyError as e:
            self.logger.error(f"Missing expected field in response: {e}")
            raise PluginError(f"Invalid response format: {e}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving task {task_id}: {e}")
            raise PluginError(f"Task retrieval failed: {e}")
```

---

## Configuration Management

### Environment Variables

Use environment variables for sensitive configuration:

```python
import os

class PluginConfig:
    def __init__(self, config: Dict[str, Any]):
        self.raw_config = config
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable substitution"""
        value = self.raw_config.get(key, default)
        
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            return os.getenv(env_var, default)
            
        return value
```

### Configuration Validation

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class LinearPluginConfig(BaseModel):
    """Linear plugin configuration schema"""
    
    api_key: str = Field(..., description="Linear API key")
    team_id: str = Field(..., description="Linear team ID")
    workspace_id: Optional[str] = Field(None, description="Linear workspace ID")
    auto_assign: bool = Field(False, description="Auto-assign tasks to AI agent")
    default_priority: str = Field("medium", description="Default task priority")
    
    class Config:
        env_prefix = "LINEAR_"
        
class LinearPlugin(TaskManagementPlugin):
    def __init__(self, config: Dict[str, Any]):
        # Validate configuration
        self.config = LinearPluginConfig(**config)
        super().__init__(self.config.dict())
```

---

## Testing Plugins

### Unit Testing Framework

```python
# tests/test_linear_plugin.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.linear_plugin import LinearPlugin

@pytest.fixture
def plugin_config():
    return {
        "api_key": "test_key",
        "team_id": "test_team",
    }

@pytest.fixture
def linear_plugin(plugin_config):
    return LinearPlugin(plugin_config)

@pytest.mark.asyncio
class TestLinearPlugin:
    
    async def test_connect_success(self, linear_plugin):
        """Test successful connection"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "data": {"teams": {"nodes": [{"id": "test_team", "name": "Test Team"}]}}
            }
            
            mock_session.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await linear_plugin.connect()
            assert result is True
            assert linear_plugin._connected is True
            
    async def test_connect_failure(self, linear_plugin):
        """Test connection failure"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.post.side_effect = Exception("Connection failed")
            
            result = await linear_plugin.connect()
            assert result is False
            assert linear_plugin._connected is False
            
    async def test_get_task(self, linear_plugin):
        """Test task retrieval"""
        # Mock the connection
        linear_plugin._connected = True
        linear_plugin.session = AsyncMock()
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "data": {
                "issue": {
                    "id": "test_id",
                    "identifier": "TEST-123",
                    "title": "Test Task",
                    "description": "Test Description",
                    "state": {"name": "In Progress"},
                    "assignee": {"email": "test@example.com"},
                    "priority": 2,
                    "labels": {"nodes": [{"name": "backend"}]},
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "dueDate": None
                }
            }
        }
        
        linear_plugin.session.post.return_value.__aenter__.return_value = mock_response
        
        task = await linear_plugin.get_task("TEST-123")
        
        assert task["id"] == "TEST-123"
        assert task["title"] == "Test Task"
        assert task["status"] == "in_progress"
        assert task["assignee"] == "test@example.com"
        
    async def test_create_task(self, linear_plugin):
        """Test task creation"""
        # Setup mocks...
        
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": "high"
        }
        
        task_id = await linear_plugin.create_task("project", task_data)
        assert task_id == "TEST-124"
```

### Integration Testing

```python
# tests/integration/test_linear_integration.py
import pytest
import os
from plugins.linear_plugin import LinearPlugin

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("LINEAR_API_KEY"),
    reason="LINEAR_API_KEY not set"
)
class TestLinearIntegration:
    
    @pytest.fixture
    def live_plugin(self):
        config = {
            "api_key": os.getenv("LINEAR_API_KEY"),
            "team_id": os.getenv("LINEAR_TEAM_ID")
        }
        return LinearPlugin(config)
        
    async def test_live_connection(self, live_plugin):
        """Test connection to live Linear API"""
        result = await live_plugin.connect()
        assert result is True
        
        await live_plugin.disconnect()
        
    async def test_live_task_operations(self, live_plugin):
        """Test CRUD operations on live Linear API"""
        await live_plugin.connect()
        
        try:
            # Create task
            task_data = {
                "title": "Integration Test Task",
                "description": "Created by integration test",
                "priority": "low"
            }
            
            task_id = await live_plugin.create_task("test_project", task_data)
            assert task_id
            
            # Get task
            task = await live_plugin.get_task(task_id)
            assert task["title"] == task_data["title"]
            
            # Update task
            result = await live_plugin.update_task_status(task_id, "in_progress")
            assert result is True
            
            # Verify update
            updated_task = await live_plugin.get_task(task_id)
            assert updated_task["status"] == "in_progress"
            
        finally:
            await live_plugin.disconnect()
```

### Mock Servers for Testing

```python
# tests/mock_server.py
from aiohttp import web
import json

class MockLinearServer:
    """Mock Linear GraphQL server for testing"""
    
    def __init__(self):
        self.app = web.Application()
        self.app.router.add_post('/graphql', self.handle_graphql)
        self.issues = {}
        
    async def handle_graphql(self, request):
        """Handle GraphQL requests"""
        data = await request.json()
        query = data.get("query", "")
        variables = data.get("variables", {})
        
        if "teams" in query:
            return web.json_response({
                "data": {
                    "teams": {
                        "nodes": [{"id": "test_team", "name": "Test Team"}]
                    }
                }
            })
            
        elif "GetIssue" in query:
            issue_id = variables.get("id")
            if issue_id in self.issues:
                return web.json_response({
                    "data": {"issue": self.issues[issue_id]}
                })
            else:
                return web.json_response({
                    "errors": [{"message": "Issue not found"}]
                }, status=404)
                
        # Handle other operations...
        
    def add_issue(self, issue_data):
        """Add mock issue"""
        self.issues[issue_data["identifier"]] = issue_data
```

---

## Best Practices

### 1. Configuration Management

```python
# Good: Use environment variables for secrets
config = {
    "api_key": os.getenv("MYSERVICE_API_KEY"),
    "base_url": "https://api.myservice.com"
}

# Bad: Hardcode sensitive values
config = {
    "api_key": "secret-key-123",
    "base_url": "https://api.myservice.com"
}
```

### 2. Error Handling

```python
# Good: Specific error types and informative messages
try:
    result = await self.api_call(params)
except aiohttp.ClientTimeout:
    raise ConnectionError("API request timed out")
except aiohttp.ClientResponseError as e:
    if e.status == 401:
        raise AuthenticationError("Invalid API credentials")
    elif e.status == 404:
        raise NotFoundError(f"Task {task_id} not found")
    else:
        raise PluginError(f"API error: {e.status} {e.message}")

# Bad: Generic error handling
try:
    result = await self.api_call(params)
except Exception as e:
    raise Exception("Something went wrong")
```

### 3. Async Best Practices

```python
# Good: Proper async/await usage
async def batch_update_tasks(self, updates):
    """Update multiple tasks concurrently"""
    tasks = []
    for task_id, status in updates.items():
        task = asyncio.create_task(self.update_task_status(task_id, status))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Bad: Sequential operations
async def batch_update_tasks(self, updates):
    results = []
    for task_id, status in updates.items():
        result = await self.update_task_status(task_id, status)
        results.append(result)
    return results
```

### 4. Resource Management

```python
# Good: Proper resource cleanup
class MyPlugin(BasePlugin):
    async def connect(self):
        self.session = aiohttp.ClientSession()
        return True
        
    async def disconnect(self):
        if self.session:
            await self.session.close()
            
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

# Usage with context manager
async with MyPlugin(config) as plugin:
    task = await plugin.get_task("TASK-123")
```

### 5. Caching

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CachedPlugin(BasePlugin):
    """Plugin with caching support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._cache = {}
        self._cache_ttl = config.get("cache_ttl", 300)  # 5 minutes
        
    def _get_cache_key(self, method: str, *args) -> str:
        """Generate cache key"""
        return f"{method}:{':'.join(str(arg) for arg in args)}"
        
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cache entry is still valid"""
        return datetime.now() - timestamp < timedelta(seconds=self._cache_ttl)
        
    async def get_task_cached(self, task_id: str) -> Dict:
        """Get task with caching"""
        cache_key = self._get_cache_key("get_task", task_id)
        
        # Check cache first
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                return data
                
        # Fetch from API
        task = await self.get_task(task_id)
        
        # Update cache
        self._cache[cache_key] = (task, datetime.now())
        
        return task
```

---

## Publishing Plugins

### Plugin Package Structure

```
my-plugin-package/
├── setup.py
├── README.md
├── LICENSE
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   └── config.yaml.example
├── tests/
│   └── test_plugin.py
└── docs/
    └── configuration.md
```

### Setup.py

```python
from setuptools import setup, find_packages

setup(
    name="ai-dev-orchestrator-myplugin",
    version="1.0.0",
    description="My Custom Plugin for AI Development Orchestrator",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "ai-dev-orchestrator>=1.0.0",
        "aiohttp>=3.8.0",
        # Plugin-specific dependencies
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "ai_dev_orchestrator.plugins": [
            "myplugin = my_plugin:MyPlugin",
        ],
    },
)
```

### Plugin Marketplace

Submit plugins to the community marketplace:

1. **Documentation**: Complete README with usage examples
2. **Testing**: Comprehensive test suite
3. **Configuration**: Clear configuration schema and examples
4. **Versioning**: Semantic versioning
5. **License**: Open source license (MIT recommended)

---

## Examples

### Complete GitHub Plugin

```python
# plugins/github_plugin.py
from core.plugin_interface import VersionControlPlugin
import aiohttp
import base64
from typing import Dict, Any, List

class GitHubPlugin(VersionControlPlugin):
    """GitHub version control integration"""
    
    PLUGIN_NAME = "github"
    PLUGIN_VERSION = "1.2.0"
    PLUGIN_DESCRIPTION = "GitHub repository management"
    REQUIRED_CONFIG = ["token"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config["token"]
        self.base_url = "https://api.github.com"
        self.session = None
        
    async def connect(self) -> bool:
        """Initialize GitHub API client"""
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "AI-Dev-Orchestrator/1.0"
                }
            )
            
            # Test connection
            async with self.session.get(f"{self.base_url}/user") as response:
                self._connected = response.status == 200
                return self._connected
                
        except Exception as e:
            self.logger.error(f"GitHub connection failed: {e}")
            return False
            
    async def create_pull_request(self, repository: str, pr_data: Dict) -> str:
        """Create pull request"""
        owner, repo = repository.split("/")
        
        payload = {
            "title": pr_data["title"],
            "body": pr_data.get("description", ""),
            "head": pr_data["source_branch"],
            "base": pr_data["target_branch"],
            "draft": pr_data.get("draft", False)
        }
        
        async with self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/pulls",
            json=payload
        ) as response:
            if response.status == 201:
                data = await response.json()
                return data["html_url"]
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create PR: {error_text}")
                
    # ... implement other methods
```

This comprehensive guide provides everything needed to develop, test, and publish custom plugins for the AI Development Automation System. The plugin architecture ensures extensibility while maintaining consistency and reliability across all integrations.