#!/usr/bin/env python3
"""
Complete End-to-End Workflow for CMMAI-48
This script demonstrates the full automated development workflow:
1. Fetch task from Jira
2. Clone repository and create branch
3. Generate and write code files
4. Commit and push changes
5. Create GitHub Pull Request
6. Update Confluence documentation
7. Update Jira task status to In Review
"""

import asyncio
import os
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import git
import shutil

from plugins.jira_plugin import JiraPlugin
from plugins.github_plugin import GitHubPlugin


class FullWorkflowRunner:
    def __init__(self):
        load_dotenv()
        self.task_id = "CMMAI-48"
        self.repo_url = "git@github.com:ThomasGooch/agenticDummy.git"
        self.repo_name = "ThomasGooch/agenticDummy"
        self.branch_name = "feature/cmmai-48-hello-world-api"
        self.workspace_dir = None
        
        # Initialize plugins
        self.jira = JiraPlugin({
            'connection': {
                'url': os.getenv('JIRA_URL'),
                'email': os.getenv('JIRA_EMAIL'),
                'api_token': os.getenv('JIRA_API_TOKEN')
            }
        })
        
        self.github = GitHubPlugin({
            'connection': {
                'token': os.getenv('GITHUB_TOKEN'),
                'api_url': 'https://api.github.com'
            }
        })

    async def run_complete_workflow(self):
        """Execute the complete end-to-end workflow"""
        
        print("🚀 Starting Complete End-to-End Workflow for CMMAI-48")
        print("=" * 70)
        
        try:
            # Initialize plugins
            await self._initialize_plugins()
            
            # Step 1: Fetch task details
            task_data = await self._fetch_task_details()
            
            # Step 2: Update task status to In Progress
            await self._update_task_status("In Progress")
            
            # Step 3: Clone repository and setup workspace
            repo_path = await self._setup_workspace()
            
            # Step 4: Create feature branch
            await self._create_branch(repo_path)
            
            # Step 5: Generate code files
            await self._generate_and_write_files(repo_path, task_data)
            
            # Step 6: Commit changes
            commit_hash = await self._commit_changes(repo_path, task_data)
            
            # Step 7: Push branch
            await self._push_branch(repo_path)
            
            # Step 8: Create Pull Request
            pr_data = await self._create_pull_request(task_data, commit_hash)
            
            # Step 9: Update Confluence (simulated)
            await self._update_confluence_docs(task_data, pr_data)
            
            # Step 10: Final task update to In Review
            await self._complete_task_update(pr_data)
            
            print("\n🎉 Complete Workflow Successfully Executed!")
            print(f"🔗 Check your PR: {pr_data.get('pr_url', 'N/A')}")
            print(f"📋 View task: https://covermymeds.atlassian.net/browse/{self.task_id}")
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()

    async def _initialize_plugins(self):
        """Initialize all required plugins"""
        print("1️⃣ Initializing plugins...")
        
        await self.jira.initialize()
        await self.github.initialize()
        
        print("✅ Plugins initialized successfully")

    async def _fetch_task_details(self):
        """Fetch task details from Jira"""
        print("2️⃣ Fetching task details from Jira...")
        
        result = await self.jira.get_task(self.task_id)
        if not result.success:
            raise Exception(f"Failed to fetch task: {result.error}")
            
        task_data = result.data
        print(f"✅ Task: {task_data.get('title')}")
        print(f"📝 Status: {task_data.get('status')}")
        
        return task_data

    async def _update_task_status(self, status):
        """Update task status in Jira"""
        print(f"3️⃣ Updating task status to {status}...")
        
        result = await self.jira.update_task_status(self.task_id, status)
        if result.success:
            print(f"✅ Task status updated to {status}")
        else:
            print(f"⚠️ Could not update status: {result.error}")

    async def _setup_workspace(self):
        """Clone repository and setup local workspace"""
        print("4️⃣ Setting up workspace and cloning repository...")
        
        # Create temporary workspace
        self.workspace_dir = tempfile.mkdtemp(prefix="cmmai48_workspace_")
        repo_path = Path(self.workspace_dir) / "agenticDummy"
        
        print(f"📁 Workspace: {self.workspace_dir}")
        print(f"🔄 Cloning {self.repo_url}...")
        
        # Clone repository using SSH
        repo = git.Repo.clone_from(self.repo_url, repo_path)
        
        print(f"✅ Repository cloned to {repo_path}")
        print(f"🌿 Current branch: {repo.active_branch}")
        
        return repo_path

    async def _create_branch(self, repo_path):
        """Create and checkout feature branch"""
        print("5️⃣ Creating feature branch...")
        
        repo = git.Repo(repo_path)
        
        # Create and checkout new branch
        new_branch = repo.create_head(self.branch_name)
        new_branch.checkout()
        
        print(f"✅ Created and checked out branch: {self.branch_name}")

    async def _generate_and_write_files(self, repo_path, task_data):
        """Generate code files and write them to repository"""
        print("6️⃣ Generating and writing code files...")
        
        # Generate Hello World FastAPI application
        main_py_content = '''"""
Hello World API - Generated by AI Development Agent
Task: CMMAI-48 - Setup hello world for agentic workflow implementation
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Hello World API",
    description="A simple Hello World API created by AI Development Agent for CMMAI-48",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


class HelloResponse(BaseModel):
    """Response model for hello world endpoint"""
    message: str
    timestamp: str
    task_id: str
    generated_by: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    service: str
    timestamp: str
    uptime: str


@app.get("/", response_model=HelloResponse)
async def hello_world() -> HelloResponse:
    """
    Hello World endpoint - main functionality for CMMAI-48
    
    Returns:
        HelloResponse: Greeting message with metadata
    """
    return HelloResponse(
        message="Hello, World! This API was created by the AI Development Agent.",
        timestamp=datetime.now().isoformat(),
        task_id="CMMAI-48",
        generated_by="AI Development Agent"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for monitoring
    
    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(
        status="healthy",
        service="hello-world-api",
        timestamp=datetime.now().isoformat(),
        uptime="running"
    )


@app.get("/api/info")
async def get_api_info() -> Dict[str, Any]:
    """
    Get API information and metadata
    
    Returns:
        Dict: API metadata and task information
    """
    return {
        "api_name": "Hello World API",
        "version": "1.0.0",
        "task_id": "CMMAI-48",
        "description": "Greenfield hello world API for agentic workflow implementation",
        "generated_by": "AI Development Agent",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Hello world message"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/api/info", "method": "GET", "description": "API information"},
        ],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == "__main__":
    print("🚀 Starting Hello World API...")
    print("📋 Task: CMMAI-48")
    print("🤖 Generated by: AI Development Agent")
    print("🔗 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=True
    )
'''

        requirements_txt_content = '''# Hello World API Dependencies
# Generated for CMMAI-48 - Hello World API

# Core FastAPI framework
fastapi>=0.104.0

# ASGI server for production
uvicorn[standard]>=0.24.0

# Data validation and settings
pydantic>=2.5.0

# Optional: for enhanced functionality
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0

# Development dependencies (optional)
pytest>=7.4.0
httpx>=0.25.0
'''

        readme_content = f'''# Hello World API

> **Generated by AI Development Agent for Task CMMAI-48**

A simple, production-ready FastAPI-based Hello World API created as part of the agentic workflow implementation.

## 📋 Task Information

- **Task ID**: CMMAI-48
- **Title**: Setup hello world for agentic workflow implementation  
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Branch**: `{self.branch_name}`

## 🚀 Features

- ✅ **Hello World Endpoint** - Main greeting functionality
- ✅ **Health Check Endpoint** - For monitoring and status checks
- ✅ **API Info Endpoint** - Metadata and endpoint documentation
- ✅ **Automatic API Documentation** - Swagger UI and ReDoc
- ✅ **Production Ready** - Uses uvicorn ASGI server
- ✅ **Type Hints** - Full Pydantic models and FastAPI integration

## 🛠️ Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python main.py
```

The API will be available at:
- **Main API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs  
- **Alternative Docs**: http://localhost:8000/redoc

### 3. Test the Endpoints

```bash
# Hello World endpoint
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# API information
curl http://localhost:8000/api/info
```

## 📡 API Endpoints

| Endpoint | Method | Description | Response Model |
|----------|--------|-------------|---------------|
| `/` | GET | Hello world greeting | `HelloResponse` |
| `/health` | GET | Health check status | `HealthResponse` |
| `/api/info` | GET | API metadata | `Dict` |

## 📖 Response Examples

### Hello World (`/`)
```json
{{
  "message": "Hello, World! This API was created by the AI Development Agent.",
  "timestamp": "2025-10-01T14:30:00.123456",
  "task_id": "CMMAI-48",
  "generated_by": "AI Development Agent"
}}
```

### Health Check (`/health`)
```json
{{
  "status": "healthy",
  "service": "hello-world-api", 
  "timestamp": "2025-10-01T14:30:00.123456",
  "uptime": "running"
}}
```

## 🏗️ Architecture

This is a greenfield FastAPI application designed to demonstrate:
- Modern Python API development practices
- Automatic OpenAPI/Swagger documentation
- Pydantic data validation
- Production-ready ASGI server setup
- Health monitoring capabilities

## 🤖 AI Agent Implementation

This API was automatically generated by the AI Development Agent as part of the agentic workflow implementation for CoverMyMeds. The implementation includes:

- ✅ **Standards Compliance**: Follows FastAPI best practices
- ✅ **Documentation**: Self-documenting with OpenAPI standards
- ✅ **Testing Ready**: Structured for easy unit and integration testing  
- ✅ **Production Ready**: Configured with uvicorn for deployment
- ✅ **Monitoring**: Health check endpoint for service monitoring

## 🚀 Next Steps

1. **Testing**: Add comprehensive unit and integration tests
2. **Deployment**: Deploy to your preferred cloud platform
3. **Monitoring**: Integrate with your monitoring and logging systems
4. **Enhancement**: Add additional endpoints as needed

## 📝 Development Notes

- Created using FastAPI framework for high performance
- Uses Pydantic for data validation and serialization
- Includes automatic API documentation generation
- Ready for containerization with Docker
- Follows REST API conventions

---

*Generated by AI Development Agent for CMMAI-48*  
*Branch: `{self.branch_name}`*  
*Repository: ThomasGooch/agenticDummy*
'''

        docker_content = '''# Dockerfile for Hello World API
# Generated for CMMAI-48

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

        # Write all files to repository
        files_to_create = {
            "main.py": main_py_content,
            "requirements.txt": requirements_txt_content,
            "README.md": readme_content,
            "Dockerfile": docker_content
        }
        
        for filename, content in files_to_create.items():
            file_path = repo_path / filename
            file_path.write_text(content.strip())
            print(f"✅ Created: {filename}")
        
        print(f"✅ Generated {len(files_to_create)} files successfully")

    async def _commit_changes(self, repo_path, task_data):
        """Commit all changes with descriptive message"""
        print("7️⃣ Committing changes...")
        
        repo = git.Repo(repo_path)
        
        # Stage all files
        repo.git.add(A=True)
        
        # Create commit message
        commit_message = f"""feat: Add Hello World API for CMMAI-48

Implement greenfield Hello World API as requested in task CMMAI-48.

Features:
- FastAPI-based REST API with Hello World endpoint
- Health check endpoint for monitoring
- API info endpoint with metadata  
- Automatic OpenAPI/Swagger documentation
- Production-ready setup with uvicorn
- Docker support for containerization

Files added:
- main.py: Core FastAPI application
- requirements.txt: Python dependencies
- README.md: Complete documentation
- Dockerfile: Container setup

Task: CMMAI-48 - {task_data.get('title', 'Setup hello world for agentic workflow implementation')}
Branch: {self.branch_name}
Generated by: AI Development Agent"""

        # Commit changes
        commit = repo.index.commit(commit_message)
        print(f"✅ Committed changes: {commit.hexsha[:8]}")
        
        return commit.hexsha

    async def _push_branch(self, repo_path):
        """Push branch to remote repository"""
        print("8️⃣ Pushing branch to remote...")
        
        repo = git.Repo(repo_path)
        origin = repo.remote('origin')
        
        # Push branch
        origin.push(self.branch_name)
        print(f"✅ Pushed branch {self.branch_name} to remote")

    async def _create_pull_request(self, task_data, commit_hash):
        """Create GitHub Pull Request"""
        print("9️⃣ Creating GitHub Pull Request...")
        
        pr_data = {
            "title": f"feat: Hello World API for CMMAI-48",
            "body": f"""## 🎯 Overview
Implement greenfield Hello World API as requested in CMMAI-48.

This PR adds a complete, production-ready FastAPI application that serves as the foundation for agentic workflow implementation.

## 📋 Task Details
- **Task ID**: CMMAI-48
- **Title**: {task_data.get('title', 'Setup hello world for agentic workflow implementation')}
- **Type**: Feature Implementation
- **Branch**: `{self.branch_name}`

## 🚀 Implementation Summary

Created a complete Hello World API with modern Python practices:

### Key Features:
- **FastAPI Framework**: High-performance async web framework
- **Automatic Documentation**: OpenAPI/Swagger UI at `/docs`
- **Health Monitoring**: Dedicated health check endpoint
- **Production Ready**: Configured with uvicorn ASGI server  
- **Docker Support**: Containerization ready
- **Type Safety**: Full Pydantic models and type hints

### API Endpoints:
- `GET /` - Hello world greeting with metadata
- `GET /health` - Service health check
- `GET /api/info` - API information and endpoint listing

## 📁 Files Added

### Core Application:
- `main.py` - FastAPI application with all endpoints
- `requirements.txt` - Python dependencies

### Documentation & Deployment:
- `README.md` - Complete setup and usage documentation
- `Dockerfile` - Container configuration

## 🧪 Testing

The API can be tested locally:

```bash
pip install -r requirements.txt
python main.py
```

Visit http://localhost:8000/docs for interactive API documentation.

## 📖 Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc  
- **README**: Complete setup and usage instructions

## ✅ Acceptance Criteria

- [x] Greenfield Hello World API created
- [x] Production-ready implementation
- [x] Complete documentation provided
- [x] Docker support included
- [x] Health check endpoint implemented
- [x] Automatic API documentation

## 🔗 Related Links

- **Jira Task**: [CMMAI-48](https://covermymeds.atlassian.net/browse/CMMAI-48)
- **Commit**: [{commit_hash[:8]}](https://github.com/{self.repo_name}/commit/{commit_hash})

---

🤖 *Generated by AI Development Agent*  
*Automated workflow implementation for agentic development*""",
            "head": self.branch_name,
            "base": "main",
            "repository": self.repo_name
        }
        
        result = await self.github.create_pull_request("/tmp", pr_data)
        
        if result.success:
            pr_url = result.data['pr_url']
            pr_number = result.data['pr_number']
            print(f"✅ Pull Request created successfully!")
            print(f"🔗 PR #{pr_number}: {pr_url}")
            
            return {
                'pr_url': pr_url,
                'pr_number': pr_number,
                'pr_id': result.data['pr_id']
            }
        else:
            raise Exception(f"Failed to create PR: {result.error}")

    async def _update_confluence_docs(self, task_data, pr_data):
        """Update Confluence documentation (simulated)"""
        print("🔟 Updating Confluence documentation...")
        
        # This would integrate with Confluence API
        confluence_content = f"""
# Hello World API Documentation

**Generated by AI Development Agent - {datetime.now().strftime('%Y-%m-%d')}**

## Project Overview

A greenfield Hello World API implementation created as part of the agentic workflow for CMMAI-48.

## Implementation Details

### Task Information
- **Task ID**: CMMAI-48
- **Title**: {task_data.get('title')}
- **Implementation Date**: {datetime.now().strftime('%Y-%m-%d')}
- **Pull Request**: [#{pr_data['pr_number']}]({pr_data['pr_url']})

### Technical Specifications
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn ASGI
- **Documentation**: OpenAPI/Swagger
- **Deployment**: Docker ready

### API Endpoints
- `GET /` - Hello world greeting
- `GET /health` - Health check
- `GET /api/info` - API metadata

### Repository
- **Repository**: ThomasGooch/agenticDummy
- **Branch**: {self.branch_name}
- **Pull Request**: {pr_data['pr_url']}

## Next Steps
1. Code review and merge PR
2. Deploy to development environment  
3. Integration testing
4. Production deployment

---
*This documentation was automatically generated by the AI Development Agent*
"""
        
        print("✅ Confluence documentation prepared")
        print("📄 Documentation includes:")
        print("  - Project overview and technical specs")
        print("  - API endpoint documentation") 
        print("  - Implementation timeline")
        print("  - Links to PR and repository")

    async def _complete_task_update(self, pr_data):
        """Final update to Jira task with PR information"""
        print("1️⃣1️⃣ Completing task update with PR information...")
        
        # Update task status to In Review
        await self.jira.update_task_status(self.task_id, "In Review")
        
        # Add final completion comment
        completion_comment = f"""🚀 **Implementation Complete - Ready for Review!**

The Hello World API has been successfully implemented and is ready for code review.

## 📊 Implementation Summary
- **Pull Request**: [#{pr_data['pr_number']}]({pr_data['pr_url']})
- **Branch**: `{self.branch_name}`
- **Files Created**: 4 (main.py, requirements.txt, README.md, Dockerfile)

## 🎯 Deliverables
✅ **FastAPI Application**: Complete Hello World API with multiple endpoints
✅ **Documentation**: Comprehensive README with setup instructions  
✅ **Production Ready**: Docker support and uvicorn configuration
✅ **API Documentation**: Automatic OpenAPI/Swagger generation
✅ **Health Monitoring**: Dedicated health check endpoint

## 🔍 Code Review Checklist
- [ ] Review API endpoint implementations
- [ ] Verify documentation completeness
- [ ] Check Docker configuration
- [ ] Validate production readiness
- [ ] Test API functionality

## 🚀 Next Steps
1. **Code Review**: Team review of implementation
2. **Testing**: Local testing and validation
3. **Deployment**: Deploy to development environment
4. **Merge**: Merge PR after approval

**Estimated Review Time**: 15-30 minutes (simple implementation)

The implementation follows FastAPI best practices and includes comprehensive documentation. Ready for review and deployment! 🎉"""

        result = await self.jira.add_comment(self.task_id, completion_comment)
        
        if result.success:
            print("✅ Task updated with completion summary")
            print("📋 Status: In Review")
        else:
            print(f"⚠️ Could not add final comment: {result.error}")

    async def _cleanup(self):
        """Clean up resources and temporary files"""
        print("🧹 Cleaning up...")
        
        # Clean up plugins
        await self.jira.cleanup()
        await self.github.cleanup()
        
        # Clean up workspace
        if self.workspace_dir and Path(self.workspace_dir).exists():
            shutil.rmtree(self.workspace_dir)
            print(f"✅ Cleaned up workspace: {self.workspace_dir}")


async def main():
    """Run the complete workflow"""
    runner = FullWorkflowRunner()
    await runner.run_complete_workflow()


if __name__ == "__main__":
    asyncio.run(main())