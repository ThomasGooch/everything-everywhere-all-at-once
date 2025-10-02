# Workflow Configuration Guide

> **Complete guide to creating and customizing workflows for the AI Development Automation System**

## Table of Contents

1. [Overview](#overview)
2. [Workflow Structure](#workflow-structure)
3. [Step Types](#step-types)
4. [Variables and Templating](#variables-and-templating)
5. [Error Handling](#error-handling)
6. [Conditional Execution](#conditional-execution)
7. [Built-in Workflows](#built-in-workflows)
8. [Custom Workflows](#custom-workflows)
9. [Testing Workflows](#testing-workflows)
10. [Best Practices](#best-practices)
11. [Examples](#examples)

---

## Overview

Workflows define the sequence of actions that agents perform to complete tasks. The AI Development Automation System uses YAML-based workflow definitions that support:

- **Plugin Actions**: Interact with external services (Jira, GitHub, Slack, etc.)
- **AI Actions**: Generate content using AI providers (Claude, OpenAI)
- **Variable Substitution**: Pass data between steps with context resolution
- **Error Handling**: Automatic retry, rollback, and circuit breaker patterns
- **Conditional Logic**: Execute steps based on conditions and success criteria
- **Cost Tracking**: Monitor and enforce AI usage budgets

### Current Implementation Status
- ✅ **AI-Powered Workflows**: Complete autonomous development task execution
- ✅ **Production Workflows**: 5+ tested workflow templates
- ✅ **Cost Management**: Real-time cost tracking and budget enforcement
- ✅ **Error Resilience**: Circuit breakers, retries, and graceful degradation

### Workflow Engine Architecture

```
YAML File → Parser → Workflow Object → Execution Engine
                                            ↓
                        Step Execution Loop
                            ↓
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
Plugin Action      AI Action           Conditional
    │                     │                     │
External API      Claude/OpenAI           Logic
    │                     │                     │
    └─────────────────────┼─────────────────────┘
                          ↓
                Variable Storage
                          ↓
                  Next Step or Complete
```

---

## Workflow Structure

### Basic Workflow Format

```yaml
name: "Workflow Name"
description: "Brief description of what this workflow does"
version: "1.0.0"

# Global variables available to all steps
variables:
  repository_url: "${task.repository_url}"
  branch_name: "feature/${task.id}"
  
# Optional metadata
metadata:
  author: "Your Name"
  created: "2024-01-15"
  tags: ["development", "automation"]

# Workflow steps
steps:
  - name: "step_name"
    description: "What this step does"
    # Step configuration...
```

### AI-Powered Development Workflow Example

```yaml
name: "AI Development Workflow"
description: "Complete autonomous development task execution with AI agents"
version: "2.0.0"

# Global variables with enhanced context resolution
variables:
  task_id: "${context.task_id}"
  repository_path: "${context.repository_path}"
  max_cost: 5.00  # Budget limit per task

# AI-powered workflow steps
steps:
  - name: "fetch_task_details"
    description: "Retrieve task information with enhanced data"
    type: "plugin_action"
    plugin: "task_management"
    action: "get_task_enhanced"
    inputs:
      task_id: "${task_id}"
    outputs:
      task: "task_data"
    on_error: "fail"
    
  - name: "analyze_codebase"
    description: "AI analyzes the codebase structure and patterns"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      repository_path: "${repository_path}"
    outputs:
      analysis: "codebase_analysis"
    cost_limit: 1.00
    on_error: "fail"
      
  - name: "generate_implementation_plan"
    description: "AI creates detailed implementation plan"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      plan: "implementation_plan"
    cost_limit: 0.50
    on_error: "retry"
    retry_count: 2
      
  - name: "generate_code_implementation"
    description: "AI generates production-ready code"
    type: "ai_action"
    inputs:
      task: "${task_data}"
      plan: "${implementation_plan}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      implementation: "generated_code"
    cost_limit: 3.00  # Most expensive step
    on_error: "retry"
    retry_count: 1
      
  - name: "create_feature_branch"
    description: "Create feature branch for implementation"
    type: "plugin_action"
    plugin: "version_control"
    action: "create_branch"
    inputs:
      repository: "${task_data.repository_url}"
      branch_name: "feature/${task_data.task_id}-${task_data.title_slug}"
      base_branch: "main"
    outputs:
      branch: "feature_branch"
    on_error: "continue"  # Branch might already exist
      
  - name: "create_pull_request"
    description: "Create pull request with AI-generated implementation"
    type: "plugin_action"
    plugin: "version_control"
    action: "create_pull_request_enhanced"
    inputs:
      repository: "${task_data.repository_url}"
      source_branch: "${feature_branch.name}"
      target_branch: "main"
      title: "${task_data.title}"
      description: "${generated_code.pr_description}"
      auto_assign_reviewers: true
    outputs:
      pr: "pull_request"
    on_error: "fail"
      
  - name: "update_task_status"
    description: "Update task status in project management system"
    type: "plugin_action"
    plugin: "task_management"
    action: "update_task_status"
    inputs:
      task_id: "${task_id}"
      status: "In Review"
      comment: "Pull request created: ${pull_request.url}"
    on_error: "continue"  # Don't fail workflow if status update fails
      
  - name: "create_documentation"
    description: "Generate and publish documentation"
    type: "plugin_action"
    plugin: "documentation"
    action: "create_page_from_template"
    inputs:
      template_type: "feature_documentation"
      space_key: "${task_data.project_key}"
      title: "${task_data.title} - Implementation Guide"
      variables:
        task_id: "${task_data.task_id}"
        implementation: "${generated_code.documentation}"
        pr_url: "${pull_request.url}"
    outputs:
      documentation: "doc_page"
    on_error: "continue"  # Documentation creation is optional
      
  - name: "notify_team"
    description: "Notify team of completed task"
    type: "plugin_action"
    plugin: "communication"
    action: "send_message"
    inputs:
      channel: "${task_data.team_channel}"
      message: |
        🤖 **Task Completed**: ${task_data.title}
        🔗 **PR**: ${pull_request.url}
        📝 **Docs**: ${doc_page.url}
        ✅ **Status**: Ready for Review
    on_error: "continue"

# Success criteria for workflow completion
success_criteria:
  - condition: "${generated_code.success}"
    description: "Code generation must succeed"
  - condition: "${pull_request.url}"
    description: "Pull request must be created"
    
# Cost management
cost_limits:
  total_budget: "${max_cost}"
  per_step_limit: 3.00
  
# Error handling configuration
error_handling:
  default_strategy: "fail"
  max_retries: 3
  retry_delay: 5  # seconds
```
    outputs:
      task: "task_data"
    on_error: "fail"
    
  - name: "validate_task"
    description: "Ensure task has required information"
    type: "conditional"
    condition: "${task_data.status == 'todo' and task_data.repository_url}"
    on_false: "skip_workflow"
    
  - name: "create_branch"
    description: "Create feature branch from main"
    plugin: "version_control"
    action: "create_branch"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      base_branch: "main"
    outputs:
      branch_url: "branch_data.url"
    on_error: "rollback"
    
  - name: "analyze_codebase"
    description: "AI analysis of existing codebase structure"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/codebase_analysis.txt"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      task: "${task_data}"
    outputs:
      analysis: "codebase_analysis"
    max_tokens: 2000
    
  - name: "generate_implementation_plan"
    description: "Create detailed implementation plan"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/implementation_plan.txt"
    inputs:
      task: "${task_data}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      plan: "implementation_plan"
    max_tokens: 3000
    
  - name: "implement_code"
    description: "Generate production-ready code"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/code_generation.txt"
    inputs:
      plan: "${implementation_plan}"
      task: "${task_data}"
      codebase_analysis: "${codebase_analysis}"
    outputs:
      code: "generated_code"
    max_tokens: 5000
    on_error: "retry"
    retry_count: 2
    
  - name: "commit_changes"
    description: "Commit generated code to branch"
    plugin: "version_control"
    action: "commit_changes"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      message: "${generated_code.commit_message}"
      files: "${generated_code.files}"
    outputs:
      commit_hash: "commit_data.hash"
      
  - name: "create_pull_request"
    description: "Create pull request for review"
    plugin: "version_control"
    action: "create_pull_request"
    inputs:
      repository: "${repository_url}"
      source_branch: "${branch_name}"
      target_branch: "main"
      title: "${pr_title}"
      description: "${generated_code.pr_description}"
      draft: false
    outputs:
      pr_url: "pr_data.url"
      pr_number: "pr_data.number"
      
  - name: "update_task_status"
    description: "Mark task as in review"
    plugin: "task_management"
    action: "update_task_status"
    inputs:
      task_id: "${task_id}"
      status: "in_review"
      comment: "Implementation completed. PR: ${pr_data.url}"
      
  - name: "notify_team"
    description: "Send notification to team channel"
    plugin: "communication"
    action: "send_message"
    inputs:
      channel: "${team_channel}"
      message: "🤖 **Task ${task_id} completed!**\n\n✅ Code implemented and committed\n🔗 **PR:** ${pr_data.url}\n👀 Ready for review!"
    on_error: "continue"
    
  - name: "create_documentation"
    description: "Generate documentation for the implementation"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/documentation.txt"
    inputs:
      task: "${task_data}"
      implementation: "${generated_code}"
      pr_url: "${pr_data.url}"
    outputs:
      docs: "documentation"
    condition: "${task_data.requires_documentation == true}"
    
  - name: "update_confluence"
    description: "Update project documentation"
    plugin: "documentation"
    action: "update_page"
    inputs:
      page_id: "${task_data.doc_page_id}"
      content: "${documentation.content}"
    condition: "${documentation}"
    on_error: "continue"
```

---

## Enhanced Step Types

The current workflow engine supports advanced step types for AI-powered automation:

### 1. Enhanced Plugin Actions

Execute actions through production-ready plugins with advanced features:

```yaml
- name: "step_name"
  type: "plugin_action"    # Explicit type declaration
  plugin: "plugin_type"    # Enhanced plugin with circuit breaker, rate limiting
  action: "action_name"    # Method name from plugin
  inputs:
    param1: "value1"
    param2: "${variable}"
  outputs:
    result: "output_variable"
  cost_limit: 1.00         # Optional cost limit for this step
  on_error: "retry"        # Error handling strategy
  retry_count: 3          # Number of retries
```

**Production Plugin Types:**
- `task_management`: ✅ **JiraPlugin** - Enhanced Jira with custom fields, circuit breakers
- `version_control`: ✅ **GitHubPlugin** - Repository analysis, auto-reviewers, branch strategies
- `documentation`: ✅ **ConfluencePlugin** - Templates, auto-labeling, cross-referencing
- `communication`: ✅ **SlackPlugin** - Channel management, message formatting
- `ai_provider`: ✅ **ClaudePlugin** - Cost tracking, prompt optimization

### 2. AI Actions

Generate content using AI providers with cost tracking and optimization:

```yaml
- name: "ai_step"
  type: "ai_action"         # AI-powered step
  description: "AI task description"
  inputs:
    task: "${task_data}"    # Task context
    context: "${analysis}"  # Additional context
  outputs:
    result: "ai_result"     # AI-generated content
  cost_limit: 2.00         # Budget limit for this AI call
  on_error: "retry"        # Retry on failure
  retry_count: 2          # AI calls are expensive, limit retries
```

**AI Action Types:**
- **Codebase Analysis**: AI analyzes repository structure and patterns
- **Implementation Planning**: AI creates detailed development plans
- **Code Generation**: AI generates production-ready code with tests
- **Documentation Generation**: AI creates comprehensive documentation
- **Code Review**: AI performs automated code review (future)

#### Example AI Actions

```yaml
# Codebase analysis with AI
- name: "analyze_codebase"
  type: "ai_action"
  inputs:
    task: "${task_data}"
    repository_path: "${repository_path}"
  outputs:
    analysis: "codebase_analysis"
  cost_limit: 1.00
  
# Implementation planning with AI
- name: "generate_plan"
  type: "ai_action"
  inputs:
    task: "${task_data}"
    codebase_analysis: "${codebase_analysis}"
  outputs:
    plan: "implementation_plan"
  cost_limit: 0.50
  
# Code generation with AI
- name: "generate_code"
  type: "ai_action"
  inputs:
    task: "${task_data}"
    plan: "${implementation_plan}"
  outputs:
    implementation: "generated_code"
  cost_limit: 3.00  # Most expensive AI operation
  type: "ai_action"
  agent: "development"  # or "planning"
  prompt_template: "./prompts/template.txt"
  inputs:
    context: "${some_variable}"
  outputs:
    result: "ai_output"
  max_tokens: 2000
  temperature: 0.7  # Optional
```

**AI Action Parameters:**
- `agent`: Which AI agent to use (`development`, `planning`)
- `prompt_template`: Path to Jinja2 template file
- `max_tokens`: Maximum tokens to generate
- `temperature`: Randomness (0.0-1.0)
- `model`: Override default model

### 3. Conditional Steps

Execute steps based on conditions.

```yaml
- name: "conditional_step"
  type: "conditional" 
  condition: "${variable == 'value'}"
  on_true: "continue"      # continue, skip, fail
  on_false: "skip_step"    # or skip_workflow

- name: "regular_step"
  # This step runs based on condition
  condition: "${some_check}"
  # ... step configuration
```

**Condition Syntax:**
- Python-like expressions
- Support for `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical operators: `and`, `or`, `not`
- String operations: `in`, `startswith`, `endswith`

### 4. Loop Steps

Repeat steps for collections.

```yaml
- name: "process_files"
  type: "loop"
  items: "${file_list}"
  item_var: "file"
  steps:
    - name: "process_file"
      plugin: "version_control"
      action: "update_file"
      inputs:
        file_path: "${file.path}"
        content: "${file.content}"
```

### 5. Parallel Steps

Execute multiple steps concurrently.

```yaml
- name: "parallel_operations"
  type: "parallel"
  steps:
    - name: "update_jira"
      plugin: "task_management"
      action: "update_task_status"
      # ... inputs
      
    - name: "notify_slack"
      plugin: "communication"
      action: "send_message"
      # ... inputs
```

---

## Variables and Templating

### Variable Scopes

**1. Global Variables** (available to all steps):
```yaml
variables:
  project_name: "my-project"
  base_branch: "main"
```

**2. Input Variables** (passed when executing workflow):
```yaml
# Passed via API or CLI
{
  "task_id": "PROJ-123",
  "repository_url": "https://github.com/org/repo"
}
```

**3. Step Outputs** (from previous steps):
```yaml
outputs:
  task_data: "task_info"  # Creates ${task_info} variable
```

### Variable Syntax

```yaml
# Simple substitution
branch_name: "${task_id}"

# Nested access
title: "${task_data.title}"

# Default values
channel: "${task_data.team_channel || '#general'}"

# String operations
branch: "feature/${task_id.lower()}"
message: "${title.upper()} - ${status}"

# Conditional assignment
priority: "${task_data.priority if task_data.priority else 'medium'}"
```

### Template Functions

```yaml
# String manipulation
name: "${task_id.upper()}"
name: "${task_id.lower()}"
name: "${task_id.replace('-', '_')}"

# Date/time
timestamp: "${now()}"
date: "${date('YYYY-MM-DD')}"
deadline: "${date_add(task.created, days=7)}"

# Collections
first_file: "${files[0]}"
file_count: "${len(files)}"
has_tests: "${'test' in file_names}"

# JSON operations
config: "${json(config_string)}"
```

### Jinja2 Templates

For complex templating, use Jinja2 templates:

```jinja2
{# prompts/code_generation.txt #}
You are implementing the following task:

**Task:** {{ task.title }}
**Description:** {{ task.description }}

**Requirements:**
{% for requirement in task.requirements %}
- {{ requirement }}
{% endfor %}

**Codebase Context:**
{{ codebase_analysis.summary }}

{% if codebase_analysis.patterns %}
**Existing Patterns:**
{% for pattern in codebase_analysis.patterns %}
- {{ pattern.name }}: {{ pattern.description }}
{% endfor %}
{% endif %}

Please provide:
1. Implementation code
2. Unit tests
3. Integration notes

**Output Format:** JSON with fields: code, tests, notes, commit_message, pr_description
```

---

## Error Handling

### Error Strategies

```yaml
- name: "risky_step"
  # ... step config
  on_error: "retry"        # retry, rollback, continue, fail
  retry_count: 3           # Number of retries
  retry_delay: 5           # Delay between retries (seconds)
  retry_backoff: true      # Exponential backoff
```

**Error Strategies:**
- `retry`: Retry the step with optional backoff
- `rollback`: Undo previous steps and fail
- `continue`: Log error and continue workflow
- `fail`: Stop workflow execution immediately

### Rollback Configuration

```yaml
- name: "create_branch"
  plugin: "version_control"
  action: "create_branch"
  # ...
  rollback:
    plugin: "version_control"
    action: "delete_branch"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
```

### Error Handling Example

```yaml
name: "Robust Development Workflow"

steps:
  - name: "create_branch"
    plugin: "version_control" 
    action: "create_branch"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
    on_error: "fail"  # Critical step, must succeed
    
  - name: "generate_code"
    type: "ai_action"
    # ... config
    on_error: "retry"
    retry_count: 3
    retry_backoff: true
    
  - name: "commit_code"
    plugin: "version_control"
    action: "commit_changes"
    # ... config
    on_error: "rollback"
    rollback:
      plugin: "version_control"
      action: "delete_branch"
      inputs:
        repository: "${repository_url}"
        branch: "${branch_name}"
        
  - name: "notify_team"
    plugin: "communication"
    action: "send_message"
    # ... config
    on_error: "continue"  # Non-critical, don't fail workflow
```

---

## Conditional Execution

### Simple Conditions

```yaml
- name: "update_documentation"
  condition: "${task.requires_docs == true}"
  plugin: "documentation"
  action: "create_page"
  # ... inputs
```

### Complex Conditions

```yaml
- name: "run_integration_tests"
  condition: "${task.type == 'feature' and 'backend' in task.labels}"
  # ... step config

- name: "deploy_to_staging"
  condition: "${pr.approved and tests.passed and not task.title.startswith('WIP')}"
  # ... step config
```

### Conditional Workflows

```yaml
- name: "check_task_type"
  type: "conditional"
  condition: "${task.type}"
  branches:
    feature:
      - name: "feature_workflow"
        workflow: "feature_development.yaml"
    bugfix:
      - name: "bugfix_workflow" 
        workflow: "bug_fix.yaml"
    hotfix:
      - name: "hotfix_workflow"
        workflow: "emergency_fix.yaml"
```

---

## Built-in Workflows

### 1. Standard Development Workflow

**File:** `workflows/standard_dev_workflow.yaml`

**Purpose:** Complete feature development from task to PR

**Steps:**
1. Fetch task details
2. Create feature branch  
3. Analyze codebase
4. Generate implementation plan
5. Generate code
6. Commit changes
7. Create pull request
8. Update task status
9. Notify team

### 2. Hotfix Workflow

**File:** `workflows/hotfix_workflow.yaml`

**Purpose:** Emergency bug fixes with expedited process

**Steps:**
1. Fetch critical bug details
2. Create hotfix branch from main
3. Generate quick fix
4. Run critical tests
5. Create PR with priority labels
6. Auto-notify on-call team

### 3. Documentation-Only Workflow

**File:** `workflows/documentation_only_workflow.yaml` 

**Purpose:** Documentation updates without code changes

**Steps:**
1. Fetch documentation task
2. Generate documentation content
3. Update documentation platform
4. Create PR for review
5. Update task status

### 4. Planning Workflow

**File:** `workflows/planning_workflow.yaml`

**Purpose:** Break down epics into detailed tasks

**Steps:**
1. Analyze epic requirements
2. Generate task breakdown
3. Create individual tasks in project management
4. Set up repository structure
5. Create documentation space
6. Notify stakeholders

---

## Custom Workflows

### Creating Custom Workflows

1. **Create YAML file** in `workflows/` directory
2. **Define workflow structure** following the standard format
3. **Test workflow** using the CLI or API
4. **Register workflow** in configuration

### Workflow Inheritance

```yaml
name: "Extended Development Workflow"
extends: "standard_dev_workflow.yaml"  # Inherit from base workflow

# Override or add variables
variables:
  enable_security_scan: true
  
# Add additional steps
additional_steps:
  - name: "security_scan"
    position: "after:generate_code"  # Insert after specific step
    plugin: "security"
    action: "scan_code"
    inputs:
      code: "${generated_code}"
    
  - name: "performance_test"
    position: "before:create_pull_request"
    plugin: "testing"
    action: "run_performance_tests"
```

### Modular Workflows

```yaml
name: "Modular Development Workflow"

# Import reusable workflow modules
includes:
  - "./modules/task_setup.yaml"
  - "./modules/code_generation.yaml" 
  - "./modules/testing.yaml"
  - "./modules/deployment.yaml"

steps:
  - include: "task_setup"
    
  - include: "code_generation"
    inputs:
      style_guide: "${project.style_guide}"
      
  - include: "testing"
    condition: "${not task.skip_tests}"
    
  - include: "deployment"
    condition: "${task.auto_deploy}"
```

### Environment-Specific Workflows

```yaml
name: "Multi-Environment Workflow"

variables:
  environment: "${env.DEPLOYMENT_ENV || 'development'}"

steps:
  - name: "determine_environment"
    type: "conditional"
    condition: "${environment}"
    branches:
      development:
        - include: "dev_workflow.yaml"
      staging:
        - include: "staging_workflow.yaml"
      production:
        - include: "production_workflow.yaml"
```

---

## Testing Workflows

### Workflow Validation

```bash
# Validate workflow syntax
ai-dev-orchestrator workflow validate workflows/my_workflow.yaml

# Test workflow with dry-run
ai-dev-orchestrator workflow test workflows/my_workflow.yaml --dry-run

# Execute workflow with test data
ai-dev-orchestrator workflow run workflows/my_workflow.yaml \
  --input test_data.json \
  --environment test
```

### Unit Testing Workflows

```python
# tests/test_workflows.py
import pytest
from core.workflow_engine import WorkflowEngine

@pytest.mark.asyncio
class TestCustomWorkflow:
    
    async def test_workflow_parsing(self):
        """Test workflow YAML parsing"""
        engine = WorkflowEngine()
        workflow = engine.load_workflow("workflows/my_workflow.yaml")
        
        assert workflow.name == "My Custom Workflow"
        assert len(workflow.steps) == 5
        
    async def test_workflow_execution(self):
        """Test workflow execution with mock data"""
        engine = WorkflowEngine()
        workflow = engine.load_workflow("workflows/my_workflow.yaml")
        
        # Mock plugin responses
        mock_context = {
            "task_id": "TEST-123",
            "repository_url": "https://github.com/test/repo"
        }
        
        result = await engine.execute_workflow(workflow, mock_context)
        assert result.success is True
        assert "pr_url" in result.outputs
        
    async def test_error_handling(self):
        """Test workflow error handling"""
        engine = WorkflowEngine()
        workflow = engine.load_workflow("workflows/error_test_workflow.yaml")
        
        # Simulate plugin error
        with pytest.raises(WorkflowExecutionError):
            await engine.execute_workflow(workflow, {})
```

### Integration Testing

```python
# tests/integration/test_workflow_integration.py
@pytest.mark.integration
class TestWorkflowIntegration:
    
    async def test_full_development_workflow(self):
        """Test complete development workflow end-to-end"""
        # Setup test environment
        test_task_id = await self.create_test_task()
        test_repo = await self.create_test_repository()
        
        try:
            # Execute workflow
            engine = WorkflowEngine()
            context = {
                "task_id": test_task_id,
                "repository_url": test_repo.url
            }
            
            result = await engine.execute_workflow(
                "standard_dev_workflow.yaml", 
                context
            )
            
            # Verify results
            assert result.success
            
            # Check that PR was created
            pr = await self.get_pull_request(test_repo, result.outputs["pr_number"])
            assert pr is not None
            
            # Check task status was updated
            task = await self.get_task(test_task_id)
            assert task.status == "in_review"
            
        finally:
            # Cleanup
            await self.cleanup_test_resources()
```

---

## Best Practices

### 1. Workflow Design

```yaml
# Good: Clear, descriptive names
name: "Feature Development with Testing"
- name: "analyze_requirements"
- name: "generate_implementation" 
- name: "run_unit_tests"

# Bad: Vague names
name: "Dev Workflow"
- name: "step1"
- name: "step2"
- name: "step3"
```

### 2. Error Handling

```yaml
# Good: Appropriate error handling for each step type
- name: "create_branch"
  on_error: "fail"          # Critical infrastructure step

- name: "generate_code" 
  on_error: "retry"         # Retry AI operations
  retry_count: 3
  
- name: "send_notification"
  on_error: "continue"      # Non-critical communication
```

### 3. Variable Management

```yaml
# Good: Clear variable scoping and defaults
variables:
  base_branch: "${project.default_branch || 'main'}"
  notification_channel: "${team.channel || '#general'}"
  
# Bad: Hardcoded values
variables:
  base_branch: "master"
  notification_channel: "#dev-team"
```

### 4. Documentation

```yaml
name: "Well Documented Workflow"
description: |
  This workflow handles standard feature development including:
  - Code generation with AI
  - Automated testing
  - PR creation and team notification
  
  Requirements:
  - Task must have repository_url
  - Team must have Slack channel configured

steps:
  - name: "validate_prerequisites"
    description: "Ensure all required information is available"
    # ... configuration
```

### 5. Security

```yaml
# Good: Use environment variables for secrets
variables:
  api_token: "${env.GITHUB_TOKEN}"
  
# Bad: Hardcode sensitive information
variables:
  api_token: "ghp_xxxxxxxxxxxx"
```

### 6. Performance

```yaml
# Good: Parallel execution for independent steps
- name: "parallel_updates"
  type: "parallel"
  steps:
    - name: "update_jira"
      plugin: "task_management"
      # ...
    - name: "update_confluence"
      plugin: "documentation"
      # ...

# Bad: Sequential execution of independent operations
- name: "update_jira"
  # ...
- name: "update_confluence"
  # ...
```

---

## Examples

### Complete E-commerce Feature Workflow

```yaml
name: "E-commerce Feature Development"
description: "Complete workflow for e-commerce feature implementation"
version: "1.0.0"

variables:
  repository_url: "${task.repository_url}"
  branch_name: "feature/${task.id}-${task.title.lower().replace(' ', '-')}"
  microservice: "${task.microservice || 'api'}"
  database_migration_required: "${task.requires_db_migration || false}"

steps:
  - name: "fetch_task_details"
    description: "Get comprehensive task information"
    plugin: "task_management"
    action: "get_task"
    inputs:
      task_id: "${task_id}"
    outputs:
      task: "task_data"
      
  - name: "validate_task_requirements"
    description: "Ensure task has all required information"
    type: "conditional"
    condition: "${task_data.acceptance_criteria and task_data.repository_url}"
    on_false: "fail"
    
  - name: "analyze_dependencies"
    description: "Identify other services that might be affected"
    type: "ai_action"
    agent: "planning"
    prompt_template: "./prompts/dependency_analysis.txt"
    inputs:
      task: "${task_data}"
      microservice_architecture: "${project.architecture}"
    outputs:
      dependencies: "dependency_analysis"
      
  - name: "create_feature_branch"
    description: "Create feature branch from develop"
    plugin: "version_control"
    action: "create_branch"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      base_branch: "develop"
    outputs:
      branch_url: "branch_info.url"
    on_error: "fail"
    
  - name: "generate_database_migration"
    description: "Create database migration if needed"
    type: "ai_action"
    agent: "development" 
    prompt_template: "./prompts/database_migration.txt"
    inputs:
      task: "${task_data}"
      existing_schema: "${project.database_schema}"
    outputs:
      migration: "db_migration"
    condition: "${database_migration_required}"
    
  - name: "implement_backend_logic"
    description: "Generate backend API implementation"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/backend_implementation.txt"
    inputs:
      task: "${task_data}"
      dependencies: "${dependency_analysis}"
      architecture: "${project.backend_patterns}"
    outputs:
      backend_code: "backend_implementation"
    max_tokens: 5000
    
  - name: "implement_frontend_components"
    description: "Generate React components and pages"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/frontend_implementation.txt"
    inputs:
      task: "${task_data}"
      backend_api: "${backend_implementation.api_spec}"
      design_system: "${project.design_system}"
    outputs:
      frontend_code: "frontend_implementation"
    condition: "${task_data.requires_frontend}"
    max_tokens: 4000
    
  - name: "generate_unit_tests"
    description: "Create comprehensive test suite"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/test_generation.txt"
    inputs:
      backend_code: "${backend_implementation}"
      frontend_code: "${frontend_implementation}"
      test_framework: "${project.test_framework}"
    outputs:
      tests: "test_suite"
    max_tokens: 3000
    
  - name: "commit_implementation"
    description: "Commit all generated code"
    plugin: "version_control"
    action: "commit_changes"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      message: |
        feat: ${task_data.title}
        
        ${task_data.description}
        
        - Implemented ${backend_implementation.summary}
        {% if frontend_implementation %}
        - Added ${frontend_implementation.summary}
        {% endif %}
        {% if db_migration %}
        - Database migration: ${db_migration.summary}
        {% endif %}
        
        Closes #${task_data.id}
      files: |
        [
          {% for file in backend_implementation.files %}
          {"path": "{{ file.path }}", "content": "{{ file.content }}"},
          {% endfor %}
          {% if frontend_implementation %}
          {% for file in frontend_implementation.files %}
          {"path": "{{ file.path }}", "content": "{{ file.content }}"},
          {% endfor %}
          {% endif %}
          {% if db_migration %}
          {"path": "{{ db_migration.file_path }}", "content": "{{ db_migration.content }}"},
          {% endif %}
          {% for file in test_suite.files %}
          {"path": "{{ file.path }}", "content": "{{ file.content }}"}{% if not loop.last %},{% endif %}
          {% endfor %}
        ]
    outputs:
      commit_hash: "commit_info.hash"
      
  - name: "run_automated_tests"
    description: "Execute test suite"
    plugin: "testing"
    action: "run_tests"
    inputs:
      repository: "${repository_url}"
      branch: "${branch_name}"
      test_suites: ["unit", "integration"]
    outputs:
      test_results: "test_results"
    on_error: "fail"
    
  - name: "create_pull_request"
    description: "Create PR with comprehensive description"
    plugin: "version_control"
    action: "create_pull_request"
    inputs:
      repository: "${repository_url}"
      source_branch: "${branch_name}"
      target_branch: "develop"
      title: "${task_data.title}"
      description: |
        ## Overview
        ${task_data.description}
        
        ## Implementation Details
        ${backend_implementation.summary}
        {% if frontend_implementation %}
        
        ## Frontend Changes
        ${frontend_implementation.summary}
        {% endif %}
        
        ## Testing
        - ✅ Unit tests: ${test_results.unit.passed}/${test_results.unit.total}
        - ✅ Integration tests: ${test_results.integration.passed}/${test_results.integration.total}
        
        ## Acceptance Criteria
        {% for criterion in task_data.acceptance_criteria %}
        - [ ] {{ criterion }}
        {% endfor %}
        
        Closes #${task_data.id}
      labels: ["feature", "${microservice}", "ai-generated"]
      reviewers: "${task_data.reviewers || project.default_reviewers}"
    outputs:
      pr_url: "pr_info.url"
      pr_number: "pr_info.number"
      
  - name: "update_task_status"
    description: "Mark task as ready for review"
    plugin: "task_management"
    action: "update_task_status"
    inputs:
      task_id: "${task_id}"
      status: "in_review"
      comment: |
        🤖 **Implementation Complete!**
        
        **Pull Request:** ${pr_info.url}
        **Branch:** ${branch_name}
        **Commit:** ${commit_info.hash}
        
        **Summary:**
        ${backend_implementation.summary}
        
        Ready for code review! 🚀
        
  - name: "notify_stakeholders"
    description: "Send notifications to relevant teams"
    type: "parallel"
    steps:
      - name: "notify_dev_team"
        plugin: "communication"
        action: "send_message"
        inputs:
          channel: "#development"
          message: |
            🚀 **New Feature Ready for Review!**
            
            **Task:** ${task_data.title}
            **PR:** ${pr_info.url}
            **Estimated Review Time:** ${backend_implementation.complexity} complexity
            
            {% if dependency_analysis.affected_services %}
            **⚠️ Affects Services:** {{ dependency_analysis.affected_services | join(', ') }}
            {% endif %}
            
      - name: "notify_product_team"
        plugin: "communication"  
        action: "send_message"
        inputs:
          channel: "#product"
          message: |
            ✨ **Feature Implementation Complete**
            
            **Feature:** ${task_data.title}
            **Status:** Ready for review
            **PR:** ${pr_info.url}
            
            The development team will review and provide feedback shortly.
        condition: "${task_data.notify_product}"
        
  - name: "create_documentation"
    description: "Generate feature documentation"
    type: "ai_action"
    agent: "development"
    prompt_template: "./prompts/feature_documentation.txt"
    inputs:
      task: "${task_data}"
      implementation: "${backend_implementation}"
      api_spec: "${backend_implementation.api_spec}"
    outputs:
      documentation: "feature_docs"
    condition: "${task_data.requires_documentation}"
    
  - name: "update_api_documentation"
    description: "Update API documentation"
    plugin: "documentation"
    action: "update_page"
    inputs:
      page_id: "${project.api_docs_page_id}"
      content: "${feature_docs.api_updates}"
    condition: "${feature_docs}"
    on_error: "continue"
```

---

## Comprehensive Workflow Testing

The system includes extensive testing for all workflow functionality:

### Current Test Coverage
- **Total Workflow Tests**: 12+ tests covering all workflow types
- **AI Integration Tests**: 5 tests for AI-powered workflows  
- **Plugin Integration Tests**: 7 tests for plugin interactions
- **Error Handling Tests**: 4 tests for failure scenarios
- **Cost Tracking Tests**: 3 tests for budget enforcement

### Running Workflow Tests

```bash
# Run all workflow tests
poetry run pytest tests/integration/test_ai_workflow_integration.py -v

# Run specific AI workflow test
poetry run pytest tests/integration/test_ai_workflow_integration.py::TestAIWorkflowIntegration::test_complete_ai_workflow_execution -v

# Run cost tracking tests
poetry run pytest tests/integration/test_ai_workflow_integration.py::TestAIWorkflowIntegration::test_ai_action_cost_tracking -v
```

---

This comprehensive workflow guide provides everything needed to create, customize, and manage AI-powered workflows in the AI Development Automation System. The production-ready workflows demonstrate the system's capability to autonomously execute complex development tasks while maintaining cost control and quality assurance.