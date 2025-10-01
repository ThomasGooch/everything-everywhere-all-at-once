# User Guide: Jira-GitHub-Confluence Development Workflow

## Overview

This guide provides step-by-step instructions for using the AI Development Orchestrator to automate the complete development workflow from Jira task management to GitHub pull request creation and Confluence documentation updates.

**Workflow Summary:**
1. Retrieve task from Jira
2. Create feature branch in GitHub
3. Generate code implementation with AI
4. Create and submit pull request
5. Update Confluence documentation
6. Notify stakeholders

---

## Prerequisites

### System Requirements
- Python 3.11 or higher
- Access to Jira, GitHub, and Confluence instances
- Appropriate API tokens and permissions

### Required Configurations
- **Jira**: API token with task read/write permissions
- **GitHub**: Personal access token with repository access
- **Confluence**: API token with page edit permissions
- **Slack** (optional): Bot token for notifications

### Environment Setup
1. Ensure all plugins are configured in `config/plugins/`
2. Set environment variables for sensitive credentials
3. Verify network connectivity to all services

---

## Step-by-Step Workflow Guide

### Step 1: Prepare Your Jira Task

**Prerequisites:**
- Task exists in Jira with appropriate status (Todo/In Progress)
- Task has clear title and description
- Repository URL is specified in task or project configuration

**Task Requirements:**
- **Title**: Descriptive summary (minimum 5 characters)
- **Description**: Detailed requirements and acceptance criteria
- **Issue Type**: Bug, Story, Task, or Epic
- **Priority**: High, Medium, Low
- **Assignee**: Can be set to AI agent email

**Recommended Task Fields:**
```
Title: Add user authentication to dashboard
Description: 
  Implement secure user login functionality with:
  - JWT token authentication
  - Password validation
  - Session management
  - Redirect to dashboard on success

Acceptance Criteria:
  - [ ] User can log in with email/password
  - [ ] Invalid credentials show error message
  - [ ] Successful login redirects to dashboard
  - [ ] Session persists across browser refresh
  - [ ] Logout functionality works correctly
```

### Step 2: Initiate the Automated Workflow

**Manual Trigger:**
```bash
# From the project root directory
python -m workflows.execute \
  --workflow-name "Standard Development Workflow" \
  --task-id "PROJECT-123" \
  --repository-url "https://github.com/yourorg/yourrepo"
```

**API Trigger:**
```bash
curl -X POST http://localhost:8000/api/workflows/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "workflow_name": "Standard Development Workflow",
    "task_id": "PROJECT-123",
    "variables": {
      "repository_url": "https://github.com/yourorg/yourrepo",
      "base_branch": "main",
      "pr_draft": false,
      "notify_team": true,
      "team_channel": "#development"
    }
  }'
```

### Step 3: Monitor Workflow Execution

**Real-time Monitoring:**
The system provides live updates through multiple channels:

1. **Console Output:**
   ```
   🚀 Starting Standard Development Workflow
   📋 Fetching task PROJECT-123 from Jira...
   ✅ Task retrieved: "Add user authentication to dashboard"
   🔧 Creating feature branch: feature/project-123-add-user-authentication
   🤖 Analyzing codebase structure...
   📝 Generating implementation plan...
   ```

2. **Slack Notifications (if configured):**
   - Workflow start notification
   - Progress updates at key milestones
   - Completion notification with PR link

3. **Jira Comments:**
   - Automatic status updates
   - Progress comments with timestamps
   - Final completion summary

### Step 4: Review Generated Implementation

**What the AI Generates:**

1. **Codebase Analysis:**
   - Project structure understanding
   - Existing patterns identification
   - Technology stack detection
   - Coding conventions discovery

2. **Implementation Plan:**
   - Files to be modified/created
   - Estimated effort and complexity
   - Key changes summary
   - Testing strategy

3. **Code Implementation:**
   - Production-ready code following project conventions
   - Comprehensive error handling
   - Security best practices
   - Performance optimizations

4. **Tests:**
   - Unit tests for new functionality
   - Integration tests where appropriate
   - Test data and fixtures
   - Coverage optimization

5. **Documentation:**
   - Code comments and docstrings
   - API documentation updates
   - README updates if needed
   - Architecture documentation

### Step 5: Automated Repository Operations

**Branch Creation:**
- Branch name format: `feature/PROJECT-123-task-title-abbreviated`
- Created from specified base branch (default: main)
- Automatically checked out for development

**Code Application:**
- Files created/modified according to implementation plan
- Changes applied with proper Git staging
- Validation of syntax and basic functionality

**Commit Creation:**
- Descriptive commit message with task details
- Includes implementation summary
- References task ID for traceability
- Lists all modified/created files

**Example Commit Message:**
```
feat: Add user authentication to dashboard

Implement secure user login functionality with JWT token 
authentication, password validation, and session management.

Implementation details:
- Added authentication middleware for route protection
- Created login/logout API endpoints with validation
- Implemented JWT token generation and verification
- Added user session management with Redis storage

Files modified:
- src/middleware/auth.js
- src/routes/user.js
- src/utils/jwt.js

Files created:
- src/controllers/auth.js
- tests/auth.test.js
- docs/authentication.md

Tests: 12/12 passed
Task ID: PROJECT-123
Generated by: AI Development Agent
```

### Step 6: Pull Request Creation and Review

**Automated PR Creation:**
The system creates a comprehensive pull request with:

**PR Title:** Matches task title for consistency

**PR Description Includes:**
- 🎯 **Overview**: Task description and context
- 📋 **Task Details**: ID, type, priority, effort estimate
- 🔧 **Implementation Summary**: Key changes and approach
- 📁 **Files Changed**: Detailed list of modifications
- 🧪 **Testing**: Test results and coverage information
- 📖 **Documentation**: Generated documentation files
- ✅ **Acceptance Criteria**: Checkboxes for review validation
- 🔗 **Related Links**: Task and commit references

**PR Labels and Assignment:**
- Automatic labeling: `ai-generated`, `automated`, task type, priority
- Assigns to task assignee or default reviewers
- Requests reviews from configured team members

**Example PR Description:**
```markdown
## 🎯 Overview
Implement secure user login functionality with JWT token authentication, 
password validation, and session management. Users can now log in securely 
and maintain authenticated sessions.

## 📋 Task Details
- **Task ID**: PROJECT-123
- **Type**: Story
- **Priority**: High
- **Estimated Effort**: 4-6 hours

## 🔧 Implementation Summary
Added comprehensive authentication system with middleware-based protection,
secure JWT token handling, and Redis-based session management.

### Key Changes:
- Created authentication middleware for route protection
- Implemented secure login/logout endpoints with validation
- Added JWT token generation and verification utilities
- Integrated Redis for session storage and management

## 📁 Files Changed

### Modified Files:
- `src/app.js`
- `src/routes/index.js`
- `package.json`

### New Files:
- `src/middleware/auth.js`
- `src/controllers/auth.js`
- `src/utils/jwt.js`
- `tests/auth.test.js`
- `docs/authentication.md`

## 🧪 Testing
✅ **Tests Status**: All Passed
📊 **Coverage**: 95%
🔍 **Test Results**: 12/12 tests passed

## 📖 Documentation
✅ Documentation updated:
- `docs/authentication.md`
- `README.md` (API endpoints section)

## ✅ Acceptance Criteria
- [x] User can log in with email/password
- [x] Invalid credentials show error message
- [x] Successful login redirects to dashboard
- [x] Session persists across browser refresh
- [x] Logout functionality works correctly

## 🔗 Related Links
- **Task**: [PROJECT-123](https://yourcompany.atlassian.net/browse/PROJECT-123)
- **Commit**: [a1b2c3d](https://github.com/yourorg/yourrepo/commit/a1b2c3d)

---

🤖 *Generated by AI Development Agent*  
*Workflow: Standard Development Workflow v1.2.0*
```

### Step 7: Confluence Documentation Update

**Automatic Documentation:**
If configured, the system updates project documentation in Confluence:

1. **API Documentation**: New endpoints and authentication requirements
2. **Architecture Updates**: Changes to system design or data flow
3. **User Guides**: Updated instructions for new features
4. **Developer Notes**: Implementation details and technical decisions

**Update Process:**
- Identifies relevant Confluence pages based on configuration
- Generates contextual updates matching existing documentation style
- Creates new sections or updates existing content
- Adds version history and change tracking

### Step 8: Stakeholder Notifications

**Slack Notification Example:**
```
🚀 **Task Implementation Complete!** 

**Task**: Add user authentication to dashboard
**PR**: [#47 - Add user authentication to dashboard](https://github.com/yourorg/yourrepo/pull/47)
**Branch**: `feature/project-123-add-user-authentication`

✅ **Tests**: 12/12 passed

**Files**: 3 modified, 5 created

**Ready for review!** 👀
CC: @john.doe @jane.smith @tech-lead
```

**Email Notification** (if watchers configured):
```
Subject: Task PROJECT-123 Implementation Complete - Add user authentication to dashboard

Hello,

The AI Development Agent has completed implementation of task PROJECT-123.

Task: Add user authentication to dashboard
Pull Request: https://github.com/yourorg/yourrepo/pull/47

Summary:
- 3 files modified
- 5 files created  
- 12/12 tests passed

The pull request is ready for review.

Best regards,
AI Development Agent
```

**Jira Update:**
Task status automatically updated to "In Review" with completion summary:

```
🚀 **Implementation Completed!**

**Pull Request Created**: [PR #47](https://github.com/yourorg/yourrepo/pull/47)
**Branch**: `feature/project-123-add-user-authentication`
**Commit**: [a1b2c3d](https://github.com/yourorg/yourrepo/commit/a1b2c3d)

## 📊 Summary
- **Files Modified**: 3
- **Files Created**: 5
- **Lines Added**: 342
- **Lines Removed**: 12

## 🧪 Testing
✅ Tests: 12/12 passed

## 👀 Ready for Review!
The implementation is complete and ready for code review. Please review 
the pull request and provide feedback.

**Estimated Review Time**: Medium complexity
```

---

## Configuration Guide

### Basic Configuration

**Jira Plugin (`config/plugins/jira.yaml`):**
```yaml
connection:
  url: "https://yourcompany.atlassian.net"
  email: "${JIRA_EMAIL}"
  api_token: "${JIRA_API_TOKEN}"

options:
  timeout: 30
  retry_attempts: 3
  page_size: 50

mappings:
  task_id: "key"
  title: "fields.summary"
  description: "fields.description"
  status: "fields.status.name"
  assignee: "fields.assignee.displayName"
  priority: "fields.priority.name"
```

**GitHub Plugin (`config/plugins/github.yaml`):**
```yaml
connection:
  token: "${GITHUB_TOKEN}"
  api_url: "https://api.github.com"

options:
  timeout: 60
  default_branch: "main"
  auto_create_branches: true
  require_pr_reviews: true
  merge_strategy: "squash"
```

**Slack Plugin (`config/plugins/slack.yaml`):**
```yaml
connection:
  token: "${SLACK_BOT_TOKEN}"
  api_url: "https://slack.com/api"

options:
  default_channel: "#development"
  timeout: 30
  mention_users: true

mappings:
  success_emoji: "✅"
  error_emoji: "❌"
  info_emoji: "ℹ️"
```

### Advanced Configuration

**Workflow Customization (`workflows/custom_dev_workflow.yaml`):**
```yaml
# Extend the standard workflow
extends: "standard_dev_workflow"

# Override specific variables
variables:
  # Custom branch naming
  branch_name: "feature/${task.project}-${task.id}-${task.title.slug}"
  
  # Custom PR settings
  pr_draft: true  # Create as draft initially
  pr_auto_merge: false
  
  # Custom notifications
  team_channel: "#frontend-team"
  notify_product: true

# Add custom steps
steps:
  # Add after code generation
  - name: "run_linting"
    description: "Run ESLint and Prettier on generated code"
    plugin: "code_quality"
    action: "lint_files"
    position: "after:generate_code_implementation"
    inputs:
      workspace_path: "${workspace.path}"
      files: "${generated_code.files}"
    on_error: "fix_automatically"

  # Add custom notification
  - name: "notify_product_team"
    description: "Notify product team of feature completion"
    plugin: "communication"
    action: "send_message"
    position: "after:create_pull_request"
    condition: "${task.type == 'story' and task.priority == 'high'}"
    inputs:
      channel: "#product"
      message: |
        🎉 **Feature Ready for Review!**
        
        **Story**: ${task.title}
        **PR**: ${pr.url}
        **Estimated Review**: ${implementation_plan.review_complexity}
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Authentication Failures

**Jira Authentication Error:**
```
Error: Authentication failed - check email and API token
```

**Solution:**
1. Verify Jira email address in configuration
2. Regenerate API token in Jira settings
3. Check token permissions for project access
4. Ensure environment variable is set correctly

**GitHub Authentication Error:**
```
Error: Authentication failed - check GitHub token
```

**Solution:**
1. Verify token format starts with `ghp_` or `github_pat_`
2. Check token expiration date
3. Ensure token has appropriate repository permissions
4. Test token with GitHub API directly

#### 2. Repository Access Issues

**Branch Creation Failed:**
```
Error: Failed to create branch: Base branch 'main' not found
```

**Solution:**
1. Verify base branch name in repository
2. Check if default branch is `master` instead of `main`
3. Ensure repository URL is accessible
4. Verify write permissions to repository

**Push Failed:**
```
Error: Push failed: remote rejected
```

**Solution:**
1. Check branch protection rules
2. Verify push permissions to repository
3. Ensure branch name follows repository conventions
4. Check for required status checks

#### 3. Task Management Issues

**Task Not Found:**
```
Error: Task PROJECT-123 not found
```

**Solution:**
1. Verify task ID format and project key
2. Check task visibility and permissions
3. Ensure task exists and is accessible
4. Verify Jira project configuration

**Status Update Failed:**
```
Error: No transition found to status 'in_progress'
```

**Solution:**
1. Check available transitions in Jira workflow
2. Verify current task status allows transition
3. Update workflow configuration for correct status names
4. Check user permissions for status changes

#### 4. Code Generation Issues

**AI Generation Timeout:**
```
Error: Code generation timed out after 600 seconds
```

**Solution:**
1. Break down complex tasks into smaller subtasks
2. Increase timeout in workflow configuration
3. Simplify task requirements and acceptance criteria
4. Check AI service availability and quotas

**Code Quality Issues:**
```
Error: Generated code failed linting checks
```

**Solution:**
1. Update AI prompts with project coding standards
2. Configure automatic code formatting in workflow
3. Add pre-commit hooks for quality checks
4. Review and update coding convention documentation

#### 5. Integration Issues

**Slack Notification Failed:**
```
Error: Channel #development not found
```

**Solution:**
1. Verify channel name and bot permissions
2. Ensure bot is invited to target channel
3. Check Slack token scopes and permissions
4. Test Slack integration independently

**Confluence Update Failed:**
```
Error: Page not found or access denied
```

**Solution:**
1. Verify page ID and space permissions
2. Check Confluence API token and user permissions
3. Ensure page exists and is editable
4. Test Confluence API access separately

### Performance Optimization

#### 1. Workflow Speed

**Slow Execution Times:**
- Reduce AI token limits for faster generation
- Enable parallel execution of independent steps
- Cache frequently accessed data (repository info, user details)
- Optimize repository cloning with shallow clones

#### 2. Resource Usage

**High Memory Consumption:**
- Limit concurrent workflow executions
- Implement workspace cleanup after completion
- Use streaming for large file operations
- Configure appropriate timeout values

#### 3. API Rate Limits

**Rate Limit Exceeded:**
- Implement exponential backoff retry strategies
- Distribute requests across multiple time periods
- Cache API responses when possible
- Monitor and adjust request frequency

### Debugging Tips

#### 1. Enable Detailed Logging

```yaml
# In base.yaml configuration
logging:
  level: "DEBUG"
  output: ["console", "file"]
  file_path: "./logs/workflow.log"
  include_timestamps: true
  include_stack_traces: true
```

#### 2. Test Individual Components

```bash
# Test Jira connection
python -m plugins.jira_plugin test_connection

# Test GitHub integration
python -m plugins.github_plugin test_repository_access

# Test workflow step by step
python -m workflows.debug \
  --workflow "Standard Development Workflow" \
  --task-id "PROJECT-123" \
  --step-by-step
```

#### 3. Validate Configuration

```bash
# Validate all plugin configurations
python -m core.config validate_plugins

# Test API connectivity
python -m core.health_check --all-plugins

# Validate workflow syntax
python -m workflows.validate standard_dev_workflow.yaml
```

---

## Best Practices

### Task Preparation

1. **Clear Requirements**: Write detailed task descriptions with specific acceptance criteria
2. **Appropriate Sizing**: Break large tasks into smaller, manageable pieces
3. **Context Inclusion**: Provide architectural context and constraints
4. **Quality Standards**: Include coding standards and review requirements

### Repository Management

1. **Branch Protection**: Configure branch protection rules for quality gates
2. **PR Templates**: Use standardized PR templates for consistency
3. **Code Reviews**: Establish review processes for AI-generated code
4. **Documentation**: Maintain up-to-date architectural documentation

### Workflow Optimization

1. **Regular Updates**: Keep plugin configurations current with API changes
2. **Performance Monitoring**: Track workflow execution times and costs
3. **Error Analysis**: Review failed workflows for pattern identification
4. **Team Training**: Ensure team understands AI-generated code review

### Security Considerations

1. **Token Management**: Use environment variables for all sensitive credentials
2. **Permission Scoping**: Grant minimal required permissions to API tokens
3. **Code Review**: Always review AI-generated code for security implications
4. **Audit Logging**: Enable comprehensive logging for security auditing

### Quality Assurance

1. **Testing Strategy**: Ensure comprehensive test coverage in generated code
2. **Code Standards**: Configure linting and formatting rules
3. **Review Process**: Implement mandatory human review for all AI-generated code
4. **Continuous Integration**: Run full test suites on all pull requests

---

## Support and Resources

### Getting Help

**Documentation:**
- [Plugin Development Guide](./plugin_development.md)
- [Workflow Configuration Reference](./workflow_guide.md)
- [API Documentation](./api/README.md)

**Community Support:**
- GitHub Issues: Report bugs and feature requests
- Slack Channel: `#ai-dev-orchestrator` for community discussion
- Documentation Wiki: Community-contributed guides and examples

**Professional Support:**
- Enterprise Support: Available for production deployments
- Custom Integration: Professional services for specific requirements
- Training Programs: Team onboarding and best practices workshops

### Additional Resources

**Example Configurations:**
- [Complex Workflow Examples](../examples/)
- [Plugin Configuration Templates](../config/plugins/)
- [Custom Prompt Templates](../prompts/)

**Integration Guides:**
- [CI/CD Integration](./ci_cd_integration.md)
- [Monitoring and Alerting](./monitoring_setup.md)
- [Enterprise Deployment](./enterprise_deployment.md)

---

*This user guide is maintained by the AI Development Orchestrator team. For updates and contributions, please see our [contributing guidelines](../CONTRIBUTING.md).*