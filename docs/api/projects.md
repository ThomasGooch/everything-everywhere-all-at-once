# Projects API

> **Project management endpoints for creating, updating, and managing development projects**

## Overview

Projects represent the top-level containers for development work. Each project can contain multiple tasks, epics, and have associated repositories, documentation spaces, and team configurations.

## Endpoints

### List Projects

```http
GET /api/v1/projects
```

Retrieve a paginated list of all projects accessible to the authenticated user.

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)
- `sort` (string, optional): Sort field (created_at, updated_at, name)
- `order` (string, optional): Sort order (asc, desc, default: desc)
- `status` (string, optional): Filter by status (active, archived, completed)
- `search` (string, optional): Search projects by name or description

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/projects?page=1&per_page=20&sort=name&order=asc" \
  -H "Authorization: Bearer your_jwt_token"
```

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "proj_123456",
      "name": "E-commerce Platform",
      "description": "Complete e-commerce solution with React and FastAPI",
      "status": "active",
      "repository_url": "https://github.com/company/ecommerce",
      "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
      "team_members": ["john@company.com", "jane@company.com"],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-16T15:45:00Z",
      "stats": {
        "total_tasks": 45,
        "completed_tasks": 23,
        "in_progress_tasks": 12,
        "pending_tasks": 10
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "pages": 1
  },
  "message": "Projects retrieved successfully",
  "timestamp": "2024-01-16T16:00:00Z"
}
```

### Create Project

```http
POST /api/v1/projects
```

Create a new development project.

**Request Body:**
```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "repository_url": "string (optional)",
  "tech_stack": ["array of strings (optional)"],
  "team_members": ["array of email strings (optional)"],
  "project_type": "string (optional, default: 'web')",
  "settings": {
    "auto_assign_tasks": "boolean (optional, default: false)",
    "require_approval": "boolean (optional, default: true)",
    "default_workflow": "string (optional)",
    "notification_channels": {
      "slack_channel": "string (optional)",
      "email_notifications": "boolean (optional, default: true)"
    }
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mobile Banking App",
    "description": "Secure mobile banking application with biometric authentication",
    "repository_url": "https://github.com/bankco/mobile-banking",
    "tech_stack": ["React Native", "Node.js", "PostgreSQL", "Redis"],
    "team_members": ["lead@bankco.com", "dev1@bankco.com", "dev2@bankco.com"],
    "project_type": "mobile",
    "settings": {
      "auto_assign_tasks": false,
      "require_approval": true,
      "default_workflow": "secure_dev_workflow",
      "notification_channels": {
        "slack_channel": "#banking-dev",
        "email_notifications": true
      }
    }
  }'
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "proj_789012",
    "name": "Mobile Banking App",
    "description": "Secure mobile banking application with biometric authentication",
    "status": "active",
    "repository_url": "https://github.com/bankco/mobile-banking",
    "tech_stack": ["React Native", "Node.js", "PostgreSQL", "Redis"],
    "team_members": ["lead@bankco.com", "dev1@bankco.com", "dev2@bankco.com"],
    "project_type": "mobile",
    "settings": {
      "auto_assign_tasks": false,
      "require_approval": true,
      "default_workflow": "secure_dev_workflow",
      "notification_channels": {
        "slack_channel": "#banking-dev",
        "email_notifications": true
      }
    },
    "created_at": "2024-01-16T16:00:00Z",
    "updated_at": "2024-01-16T16:00:00Z",
    "stats": {
      "total_tasks": 0,
      "completed_tasks": 0,
      "in_progress_tasks": 0,
      "pending_tasks": 0
    }
  },
  "message": "Project created successfully",
  "timestamp": "2024-01-16T16:00:00Z"
}
```

### Get Project

```http
GET /api/v1/projects/{project_id}
```

Retrieve detailed information about a specific project.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Query Parameters:**
- `include_tasks` (boolean, optional): Include recent tasks in response
- `include_stats` (boolean, optional): Include detailed statistics

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/projects/proj_123456?include_tasks=true&include_stats=true" \
  -H "Authorization: Bearer your_jwt_token"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "proj_123456",
    "name": "E-commerce Platform",
    "description": "Complete e-commerce solution with React and FastAPI",
    "status": "active",
    "repository_url": "https://github.com/company/ecommerce",
    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
    "team_members": ["john@company.com", "jane@company.com"],
    "project_type": "web",
    "settings": {
      "auto_assign_tasks": true,
      "require_approval": true,
      "default_workflow": "standard_dev_workflow",
      "notification_channels": {
        "slack_channel": "#ecommerce-dev",
        "email_notifications": true
      }
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T15:45:00Z",
    "recent_tasks": [
      {
        "id": "task_456789",
        "title": "Implement product search functionality",
        "status": "in_progress",
        "assignee": "jane@company.com",
        "created_at": "2024-01-16T14:00:00Z"
      }
    ],
    "detailed_stats": {
      "total_tasks": 45,
      "completed_tasks": 23,
      "in_progress_tasks": 12,
      "pending_tasks": 10,
      "task_completion_rate": 0.51,
      "average_completion_time": 72, // hours
      "active_agents": 2,
      "total_cost": 245.67,
      "monthly_cost": 89.23
    }
  },
  "message": "Project retrieved successfully",
  "timestamp": "2024-01-16T16:00:00Z"
}
```

### Update Project

```http
PUT /api/v1/projects/{project_id}
```

Update an existing project's information.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Request Body:**
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "repository_url": "string (optional)",
  "tech_stack": ["array of strings (optional)"],
  "team_members": ["array of email strings (optional)"],
  "status": "string (optional: active, archived, completed)",
  "settings": {
    "auto_assign_tasks": "boolean (optional)",
    "require_approval": "boolean (optional)",
    "default_workflow": "string (optional)",
    "notification_channels": {
      "slack_channel": "string (optional)",
      "email_notifications": "boolean (optional)"
    }
  }
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/projects/proj_123456" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Complete e-commerce solution with React, FastAPI, and AI-powered recommendations",
    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL", "Redis", "TensorFlow"],
    "team_members": ["john@company.com", "jane@company.com", "ai-engineer@company.com"],
    "settings": {
      "auto_assign_tasks": true,
      "default_workflow": "enhanced_dev_workflow"
    }
  }'
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "proj_123456",
    "name": "E-commerce Platform",
    "description": "Complete e-commerce solution with React, FastAPI, and AI-powered recommendations",
    "status": "active",
    "repository_url": "https://github.com/company/ecommerce",
    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL", "Redis", "TensorFlow"],
    "team_members": ["john@company.com", "jane@company.com", "ai-engineer@company.com"],
    "project_type": "web",
    "settings": {
      "auto_assign_tasks": true,
      "require_approval": true,
      "default_workflow": "enhanced_dev_workflow",
      "notification_channels": {
        "slack_channel": "#ecommerce-dev",
        "email_notifications": true
      }
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T16:30:00Z"
  },
  "message": "Project updated successfully",
  "timestamp": "2024-01-16T16:30:00Z"
}
```

### Delete Project

```http
DELETE /api/v1/projects/{project_id}
```

Delete a project and all associated data. This action is irreversible.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Query Parameters:**
- `force` (boolean, optional): Force deletion even if project has active tasks

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/projects/proj_123456?force=false" \
  -H "Authorization: Bearer your_jwt_token"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "proj_123456",
    "deleted_at": "2024-01-16T16:45:00Z",
    "cleanup_jobs": [
      {
        "type": "tasks_cleanup",
        "status": "completed",
        "items_processed": 45
      },
      {
        "type": "files_cleanup", 
        "status": "completed",
        "items_processed": 127
      }
    ]
  },
  "message": "Project deleted successfully",
  "timestamp": "2024-01-16T16:45:00Z"
}
```

### Generate Project Plan

```http
POST /api/v1/projects/{project_id}/generate-plan
```

Use AI to generate a comprehensive project plan with epics and tasks based on requirements.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Request Body:**
```json
{
  "requirements": ["array of requirement strings (required)"],
  "constraints": ["array of constraint strings (optional)"],
  "timeline": "string (optional: 'sprint', '2-weeks', '1-month', '3-months')",
  "complexity": "string (optional: 'simple', 'medium', 'complex')",
  "methodology": "string (optional: 'agile', 'waterfall', 'kanban')",
  "generate_tasks": "boolean (optional, default: true)",
  "auto_assign": "boolean (optional, default: false)"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/projects/proj_123456/generate-plan" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": [
      "User authentication with OAuth2 and JWT",
      "Product catalog with advanced search and filtering",
      "Shopping cart with persistent storage",
      "Payment integration with Stripe and PayPal",
      "Order management system",
      "Admin dashboard for inventory management",
      "Email notifications for order updates",
      "Product recommendations using ML"
    ],
    "constraints": [
      "Must be mobile-responsive",
      "GDPR compliant",
      "Support for multiple languages"
    ],
    "timeline": "3-months",
    "complexity": "complex",
    "methodology": "agile",
    "generate_tasks": true,
    "auto_assign": false
  }'
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "plan_id": "plan_987654",
    "project_id": "proj_123456",
    "generated_at": "2024-01-16T17:00:00Z",
    "methodology": "agile",
    "timeline": {
      "estimated_duration": "12 weeks",
      "sprints": 6,
      "sprint_duration": "2 weeks"
    },
    "architecture": {
      "frontend": "React with TypeScript",
      "backend": "FastAPI with Python",
      "database": "PostgreSQL with Redis caching",
      "deployment": "Docker containers on Kubernetes",
      "monitoring": "Prometheus and Grafana"
    },
    "epics": [
      {
        "id": "epic_001",
        "title": "User Authentication System",
        "description": "Complete user authentication with OAuth2, JWT, and social login",
        "priority": "high",
        "estimated_effort": "3 weeks",
        "dependencies": [],
        "acceptance_criteria": [
          "Users can register with email/password",
          "OAuth2 integration with Google, Facebook",
          "JWT token-based authentication",
          "Password reset functionality",
          "Email verification"
        ]
      },
      {
        "id": "epic_002", 
        "title": "Product Management",
        "description": "Product catalog, search, filtering, and recommendations",
        "priority": "high",
        "estimated_effort": "4 weeks",
        "dependencies": ["epic_001"],
        "acceptance_criteria": [
          "Product CRUD operations",
          "Advanced search with filters",
          "Category management",
          "Product images and galleries",
          "ML-based recommendations"
        ]
      }
    ],
    "tasks": [
      {
        "id": "task_001001",
        "epic_id": "epic_001",
        "title": "Set up authentication database schema",
        "description": "Create database tables for users, roles, and permissions",
        "type": "backend",
        "priority": "high",
        "estimated_effort": "4 hours",
        "dependencies": [],
        "acceptance_criteria": [
          "User table with required fields",
          "Role-based permission system",
          "Database migrations created",
          "Indexes for performance"
        ],
        "technical_notes": {
          "files_to_modify": [
            "models/user.py",
            "migrations/001_create_users.py",
            "schemas/auth.py"
          ],
          "testing_requirements": [
            "Unit tests for models",
            "Integration tests for auth flow"
          ]
        }
      }
    ],
    "risks": [
      {
        "type": "technical",
        "description": "ML recommendation system complexity",
        "impact": "medium",
        "mitigation": "Start with simple collaborative filtering, enhance later"
      },
      {
        "type": "timeline",
        "description": "Payment integration may require additional compliance work",
        "impact": "high", 
        "mitigation": "Begin compliance research early, consider third-party solutions"
      }
    ],
    "recommendations": [
      "Implement authentication first as it's required by most other features",
      "Use feature flags for gradual ML recommendation rollout",
      "Set up CI/CD pipeline early in the project",
      "Consider using a design system for consistent UI components"
    ],
    "cost_estimate": {
      "development_hours": 480,
      "ai_agent_hours": 120,
      "estimated_cost": "$72,000",
      "ai_cost": "$2,400"
    }
  },
  "message": "Project plan generated successfully",
  "timestamp": "2024-01-16T17:00:00Z"
}
```

### Get Project Statistics

```http
GET /api/v1/projects/{project_id}/stats
```

Get comprehensive statistics and metrics for a project.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Query Parameters:**
- `period` (string, optional): Time period (last_7_days, last_30_days, last_90_days, all_time)
- `include_cost_breakdown` (boolean, optional): Include detailed cost analysis

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/projects/proj_123456/stats?period=last_30_days&include_cost_breakdown=true" \
  -H "Authorization: Bearer your_jwt_token"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_123456",
    "period": "last_30_days",
    "generated_at": "2024-01-16T17:30:00Z",
    "task_metrics": {
      "total_tasks": 45,
      "completed_tasks": 23,
      "in_progress_tasks": 12,
      "pending_tasks": 10,
      "completion_rate": 0.51,
      "average_completion_time_hours": 72,
      "tasks_created_this_period": 15,
      "tasks_completed_this_period": 18
    },
    "agent_metrics": {
      "total_agent_executions": 28,
      "successful_executions": 25,
      "failed_executions": 3,
      "success_rate": 0.89,
      "average_execution_time_minutes": 45,
      "active_agents": 2
    },
    "code_metrics": {
      "lines_of_code_added": 15420,
      "lines_of_code_removed": 2340,
      "files_modified": 127,
      "commits_created": 34,
      "pull_requests_created": 18,
      "pull_requests_merged": 15
    },
    "cost_breakdown": {
      "total_cost": 245.67,
      "ai_provider_costs": {
        "anthropic_claude": 198.45,
        "openai": 47.22
      },
      "infrastructure_costs": {
        "compute": 125.30,
        "storage": 15.45,
        "networking": 8.90
      },
      "cost_per_task": 10.68,
      "projected_monthly_cost": 89.23
    },
    "team_productivity": {
      "average_tasks_per_developer": 2.3,
      "most_productive_day": "Tuesday",
      "peak_hours": "10:00-12:00 UTC",
      "team_velocity": 23.5
    },
    "quality_metrics": {
      "average_pr_review_time_hours": 8.5,
      "pr_approval_rate": 0.94,
      "bug_rate": 0.08,
      "test_coverage": 0.87
    }
  },
  "message": "Project statistics retrieved successfully",
  "timestamp": "2024-01-16T17:30:00Z"
}
```

### Archive Project

```http
POST /api/v1/projects/{project_id}/archive
```

Archive a completed project while preserving all data for future reference.

**Path Parameters:**
- `project_id` (string, required): Unique project identifier

**Request Body:**
```json
{
  "reason": "string (optional)",
  "archive_tasks": "boolean (optional, default: true)",
  "preserve_repository": "boolean (optional, default: true)",
  "notification_message": "string (optional)"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/projects/proj_123456/archive" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Project completed successfully and deployed to production",
    "archive_tasks": true,
    "preserve_repository": true,
    "notification_message": "E-commerce platform project has been successfully completed and archived"
  }'
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "proj_123456",
    "status": "archived",
    "archived_at": "2024-01-16T18:00:00Z",
    "archive_summary": {
      "tasks_archived": 45,
      "files_preserved": 347,
      "repository_status": "preserved",
      "final_statistics": {
        "total_cost": 5420.67,
        "completion_rate": 1.0,
        "duration_days": 89
      }
    },
    "notifications_sent": [
      {
        "channel": "slack",
        "recipient": "#ecommerce-dev",
        "status": "sent"
      },
      {
        "channel": "email", 
        "recipients": ["john@company.com", "jane@company.com"],
        "status": "sent"
      }
    ]
  },
  "message": "Project archived successfully",
  "timestamp": "2024-01-16T18:00:00Z"
}
```

## Error Responses

### Validation Errors

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "name": ["This field is required"],
      "repository_url": ["Invalid URL format"],
      "team_members": ["Invalid email format: 'not-an-email'"]
    }
  },
  "timestamp": "2024-01-16T17:00:00Z"
}
```

### Project Not Found

```json
{
  "success": false,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "Project with ID 'proj_invalid' not found"
  },
  "timestamp": "2024-01-16T17:00:00Z"
}
```

### Insufficient Permissions

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "You don't have permission to modify this project"
  },
  "timestamp": "2024-01-16T17:00:00Z"
}
```

## SDK Examples

### Python SDK

```python
from ai_dev_orchestrator import Client

client = Client(api_key="your_api_key")

# Create project
project = await client.projects.create({
    "name": "My New Project",
    "description": "A great new project",
    "repository_url": "https://github.com/myorg/project",
    "tech_stack": ["Python", "FastAPI"]
})

# Generate project plan
plan = await client.projects.generate_plan(
    project.id,
    requirements=[
        "User authentication",
        "REST API endpoints", 
        "Database integration"
    ],
    timeline="1-month"
)

# Get project statistics
stats = await client.projects.get_stats(
    project.id,
    period="last_30_days",
    include_cost_breakdown=True
)

print(f"Project completion rate: {stats.task_metrics.completion_rate}")
```

### JavaScript SDK

```javascript
import { AIDevOrchestrator } from 'ai-dev-orchestrator-client';

const client = new AIDevOrchestrator({ apiKey: 'your_api_key' });

// Create project
const project = await client.projects.create({
  name: 'My New Project',
  description: 'A great new project',
  repositoryUrl: 'https://github.com/myorg/project',
  techStack: ['Node.js', 'Express', 'MongoDB']
});

// Generate project plan  
const plan = await client.projects.generatePlan(project.id, {
  requirements: [
    'User authentication',
    'REST API endpoints',
    'Database integration'
  ],
  timeline: '1-month'
});

// Get project statistics
const stats = await client.projects.getStats(project.id, {
  period: 'last_30_days',
  includeCostBreakdown: true
});

console.log(`Project completion rate: ${stats.taskMetrics.completionRate}`);
```

This comprehensive Projects API documentation covers all project management operations with detailed examples, error handling, and SDK usage patterns.