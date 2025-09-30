# API Documentation

> **Complete API reference for the AI Development Automation System**

## Overview

The AI Development Automation System provides a comprehensive REST API for managing projects, tasks, agents, workflows, and plugins. The API is built with FastAPI and includes automatic OpenAPI documentation.

## API Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

All API endpoints require authentication using JWT tokens.

```bash
# Get access token
curl -X POST "/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in requests
curl -H "Authorization: Bearer your_jwt_token" \
  "http://localhost:8000/api/v1/projects"
```

## API Documentation Structure

### Core Endpoints
- [**Projects**](./projects.md) - Project management operations
- [**Tasks**](./tasks.md) - Task lifecycle management
- [**Agents**](./agents.md) - AI agent operations
- [**Workflows**](./workflows.md) - Workflow execution and management

### System Endpoints
- [**Plugins**](./plugins.md) - Plugin management and configuration
- [**System**](./system.md) - Health checks, metrics, and system info
- [**Users**](./users.md) - User management and authentication

### Utility Endpoints
- [**WebSocket**](./websocket.md) - Real-time updates and notifications
- [**Files**](./files.md) - File upload and management
- [**Costs**](./costs.md) - Cost tracking and budget management

## Quick Reference

### Common Endpoints

```http
# Projects
GET    /api/v1/projects                    # List projects
POST   /api/v1/projects                    # Create project
GET    /api/v1/projects/{id}               # Get project details
PUT    /api/v1/projects/{id}               # Update project
DELETE /api/v1/projects/{id}               # Delete project

# Tasks
GET    /api/v1/tasks                       # List tasks
POST   /api/v1/tasks                       # Create task
GET    /api/v1/tasks/{id}                  # Get task details
PUT    /api/v1/tasks/{id}                  # Update task
POST   /api/v1/tasks/{id}/assign-to-agent  # Assign to AI agent

# Agents
GET    /api/v1/agents                      # List agents
GET    /api/v1/agents/{id}/status          # Get agent status
POST   /api/v1/agents/{id}/stop            # Stop agent execution

# Workflows
GET    /api/v1/workflows                   # List workflows
POST   /api/v1/workflows/execute           # Execute workflow
GET    /api/v1/workflows/{id}/status       # Get execution status

# System
GET    /api/v1/health                      # Health check
GET    /api/v1/metrics                     # System metrics
GET    /api/v1/costs                       # Cost tracking
```

### Response Format

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": ["This field is required"]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

## Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Authenticated users**: 1000 requests per hour
- **Unauthenticated users**: 100 requests per hour
- **Agent operations**: 50 concurrent operations per user

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642253400
```

## Pagination

List endpoints support pagination:

```http
GET /api/v1/projects?page=1&per_page=20&sort=created_at&order=desc
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

## Interactive Documentation

The API provides interactive documentation powered by Swagger UI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## SDK and Client Libraries

Official SDKs are available for popular languages:

- **Python**: `pip install ai-dev-orchestrator-client`
- **Node.js**: `npm install ai-dev-orchestrator-client`
- **Go**: `go get github.com/yourorg/ai-dev-orchestrator-go`
- **Java**: Maven and Gradle artifacts available

## WebSocket Events

Real-time updates are available via WebSocket connection:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event, 'Data:', data.data);
};
```

Common events:
- `agent.status_update` - Agent status changes
- `task.status_update` - Task status changes  
- `workflow.step_completed` - Workflow step completion
- `system.alert` - System alerts and notifications

## Examples

### Create and Execute a Complete Workflow

```bash
# 1. Create a new project
PROJECT_ID=$(curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-commerce Platform",
    "description": "Complete e-commerce solution",
    "repository_url": "https://github.com/company/ecommerce",
    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"]
  }' | jq -r '.data.id')

# 2. Generate project plan
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/generate-plan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": [
      "User authentication system",
      "Product catalog with search",
      "Shopping cart functionality",
      "Payment processing integration",
      "Admin dashboard"
    ]
  }'

# 3. Get generated tasks
TASKS=$(curl -X GET "http://localhost:8000/api/v1/tasks?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.data')

# 4. Assign first task to AI agent
TASK_ID=$(echo $TASKS | jq -r '.[0].id')
curl -X POST "http://localhost:8000/api/v1/tasks/$TASK_ID/assign-to-agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "development",
    "workflow": "standard_dev_workflow",
    "priority": "high"
  }'

# 5. Monitor agent progress
curl -X GET "http://localhost:8000/api/v1/agents/status?task_id=$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## Error Handling Best Practices

### Retry Logic

```python
import asyncio
import aiohttp
from typing import Optional

class APIClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        
    async def request_with_retry(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[dict] = None,
        max_retries: int = 3
    ):
        """Make API request with exponential backoff retry"""
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method, 
                        f"{self.base_url}{endpoint}",
                        json=data,
                        headers=self.headers
                    ) as response:
                        
                        if response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 60))
                            await asyncio.sleep(retry_after)
                            continue
                            
                        elif response.status >= 500:  # Server error
                            if attempt < max_retries:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                                
                        response.raise_for_status()
                        return await response.json()
                        
            except aiohttp.ClientError as e:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
                
        raise Exception(f"Max retries exceeded for {method} {endpoint}")
```

### Validation Errors

```python
# Handle validation errors
try:
    response = await client.request_with_retry(
        "POST", 
        "/api/v1/projects",
        data={"name": "My Project"}  # Missing required fields
    )
except aiohttp.ClientResponseError as e:
    if e.status == 422:
        error_details = await e.json()
        for field, errors in error_details['error']['details'].items():
            print(f"Field '{field}': {', '.join(errors)}")
    else:
        raise
```

## Testing

### Unit Testing API Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_project():
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "description": "A test project",
            "repository_url": "https://github.com/test/repo"
        },
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert "id" in response.json()["data"]
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete project creation and task execution"""
    
    # Create project
    project = await api_client.create_project({
        "name": "Integration Test Project",
        "description": "Testing full workflow",
        "repository_url": "https://github.com/test/integration"
    })
    
    # Generate tasks
    await api_client.generate_project_plan(
        project["id"],
        requirements=["Implement user auth", "Create API endpoints"]
    )
    
    # Get tasks
    tasks = await api_client.get_tasks(project_id=project["id"])
    assert len(tasks) > 0
    
    # Assign task to agent
    result = await api_client.assign_task_to_agent(
        tasks[0]["id"],
        agent_type="development"
    )
    
    # Wait for completion (with timeout)
    completion_timeout = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < completion_timeout:
        agent_status = await api_client.get_agent_status(tasks[0]["id"])
        if agent_status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(10)
    
    assert agent_status["status"] == "completed"
    assert "pr_url" in agent_status["result"]
```

This API documentation structure provides comprehensive coverage of all endpoints with examples, best practices, and testing approaches. Each individual endpoint documentation file would contain detailed specifications, request/response schemas, and usage examples.