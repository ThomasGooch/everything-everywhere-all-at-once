# AI Development Orchestrator - Project Context

## Project Overview

This is the **AI Development Automation System** - a universal, plugin-based automation platform that orchestrates the entire software development lifecycle using Claude AI. The system is designed to be production-ready, enterprise-scale automation that works with any tool combination through standardized plugin interfaces.

## Current Phase Status

**Phase 1: COMPLETED** ✅
- Core plugin system and interfaces implemented
- AgentContext orchestrator built  
- Configuration management system working
- Plugin registry and lifecycle management complete
- Project structure and foundation established

**Phase 2: COMPLETED** ✅
- Core plugins implemented (Jira, GitHub, Slack, Confluence, Claude)
- Enhanced plugins with advanced features (repository analysis, auto-reviewers, templates)
- Comprehensive test suites (417 tests passing)
- CI/CD pipeline with automated quality gates
- Workflow engine for AI-powered development automation
- Cost tracking and budget management system

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI for API server
- **Database**: PostgreSQL with SQLAlchemy & Alembic
- **Caching**: Redis
- **AI Integration**: Anthropic Claude API
- **Version Control**: GitPython for Git operations
- **Template Engine**: Jinja2 for prompt templates
- **Testing**: pytest with asyncio support
- **Code Quality**: black, flake8, mypy
- **Dependency Management**: Poetry

## Architecture Patterns

### 1. Plugin System Architecture
```python
# All plugins inherit from BasePlugin and implement specific interfaces
class BasePlugin(ABC):
    - Abstract base with common functionality
    - Configuration validation and management
    - Health checking and connection testing
    - Standardized initialization and cleanup

# Specialized plugin types:
- TaskManagementPlugin (Jira, Linear)
- VersionControlPlugin (GitHub, GitLab)  
- CommunicationPlugin (Slack, Teams)
- DocumentationPlugin (Confluence, Notion)
- AIProviderPlugin (Claude, OpenAI)
```

### 2. Central Orchestration Pattern
```python
# AgentContext manages all system components
class AgentContext:
    - Plugin lifecycle management
    - Configuration distribution
    - System health monitoring
    - Resource cleanup and error handling
```

### 3. Configuration Management
- Hierarchical YAML configuration (base + environment overrides)
- Environment variable substitution
- Plugin-specific configuration validation
- Hot-reload capabilities

## Code Style and Conventions

### 1. Naming Conventions
- **Classes**: PascalCase (e.g., `TaskManagementPlugin`, `AgentContext`)
- **Functions/Methods**: snake_case (e.g., `get_task`, `health_check`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `PLUGIN_TYPE`)
- **Files**: snake_case (e.g., `plugin_interface.py`)

### 2. Error Handling Pattern
```python
# Consistent error hierarchy
class PluginError(Exception): pass
class PluginValidationError(PluginError): pass
class PluginConnectionError(PluginError): pass

# Standard result format
class PluginResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### 3. Async/Await Pattern
- All I/O operations are async
- Proper exception handling in async methods
- Context managers for resource management
- Graceful cleanup and shutdown

### 4. Testing Patterns
- Unit tests with mocked dependencies
- Integration tests with live services (marked)
- Pytest fixtures for common test setups
- High test coverage (90%+ target)

## Project Structure

```
├── core/                    # Core system components
│   ├── plugin_interface.py  # Base plugin interfaces
│   ├── plugin_registry.py   # Plugin discovery and management
│   ├── agent_context.py     # Central orchestrator
│   └── config.py           # Configuration management
├── plugins/                 # Plugin implementations
├── agents/                  # AI agent implementations
├── tests/                   # Test suites
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── performance/        # Performance tests
├── config/                  # Configuration files
├── workflows/              # Workflow templates
├── monitoring/             # Metrics and monitoring
└── docs/                   # Documentation
```

## Development Guidelines

### 1. TDD Approach
1. **Red**: Write failing test first
2. **Green**: Implement minimum code to pass
3. **Refactor**: Clean up and optimize code
4. Run full test suite after each cycle

### 2. Plugin Development
- Always extend appropriate base class
- Implement all abstract methods
- Include comprehensive configuration validation
- Add health check functionality
- Write unit tests with mocked external services
- Include integration tests (marked appropriately)

### 3. Configuration Management
- Use environment variables for secrets
- Validate all configuration on startup
- Support environment-specific overrides
- Document all configuration options

### 4. Error Handling
- Use specific exception types
- Log errors with appropriate levels
- Provide meaningful error messages
- Implement retry logic where appropriate

## External Dependencies

### Required Services
- **PostgreSQL**: Main database
- **Redis**: Caching and session storage
- **Anthropic API**: Claude AI integration

### External APIs
- **Jira**: Task management integration
- **GitHub**: Version control operations
- **Slack**: Team communication

## Security Considerations

- All credentials encrypted at rest
- JWT tokens for API authentication
- Rate limiting on external API calls
- Input validation and sanitization
- Audit logging for all operations

## Performance Requirements

- Sub-second API response times
- Support for concurrent plugin operations
- Efficient database connection pooling
- Memory usage optimization
- Cost tracking for AI API usage

## Current Implementation Status

### ✅ Completed (Phase 1)
- Plugin interface definitions and base classes
- Plugin registry with discovery and lifecycle management
- AgentContext orchestrator with initialization/cleanup
- Configuration management with YAML support
- Project structure and development environment

### ✅ Completed (Phase 2)
- Enhanced plugin implementations:
  - **JiraPlugin**: Advanced task management with custom fields, story points, team assignments
  - **GitHubPlugin**: Repository analysis, auto-reviewer assignment, branch strategies
  - **SlackPlugin**: Team communication with channel management and formatting
  - **ConfluencePlugin**: Documentation automation with templates and auto-labeling
  - **ClaudePlugin**: AI code generation with cost tracking and prompt optimization
- Comprehensive test coverage (417 tests passing, 1 skipped)
- Automated CI/CD pipeline with quality gates
- Workflow engine for AI-powered task execution
- Integration testing framework with mock services

### 🚧 In Progress (Phase 3)
- Web UI dashboard development
- Multi-repository project support
- Advanced error recovery mechanisms
- Performance optimization

### 📋 Next Steps (Phase 4)
- Multi-agent collaboration framework
- Autonomous bug fixing capabilities
- Advanced security and audit features
- Enterprise multi-tenant support
- Performance monitoring and optimization

## Testing Commands

```bash
# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest tests/unit

# Run with coverage
poetry run pytest --cov=core --cov=agents --cov=plugins

# Run integration tests (requires live services)
poetry run pytest tests/integration -m integration

# Type checking
poetry run mypy core/ agents/ plugins/

# Code formatting
poetry run black core/ agents/ plugins/ tests/

# Import sorting
poetry run isort core/ agents/ plugins/ tests/

# Linting
poetry run flake8 core/ agents/ plugins/

# Security scanning
poetry run bandit -r core/ agents/ plugins/
```

## Recent Quality Improvements

### CI/CD Pipeline Enhancements (Latest)
- ✅ **Fixed all test failures**: Resolved 5 critical test failures in Jira and Slack plugins
- ✅ **Enhanced mock testing**: Implemented proper AsyncContextManagerMock for async HTTP calls
- ✅ **Circuit breaker testing**: Addressed complex retry mechanism interactions
- ✅ **Formatting compliance**: Applied Black formatting across all test files
- ✅ **Quality gates**: All CI checks now pass (formatting, linting, sorting, security, testing)

### Test Suite Status
- **Total Tests**: 417 passing, 1 skipped
- **Coverage**: Comprehensive unit and integration test coverage
- **Quality**: Zero linting errors, proper formatting, secure code patterns
- **Reliability**: Robust async test patterns with proper mocking

### Plugin Test Improvements
- **JiraPlugin**: Fixed session mocking, authentication setup, and response structure
- **SlackPlugin**: Corrected error message assertions and response handling
- **GitHub/Confluence**: Maintained existing test reliability
- **Integration Tests**: Enhanced plugin interaction testing

## Key Implementation Notes

1. **Plugin Isolation**: Each plugin runs in its own context to prevent failures from affecting others
2. **Configuration Security**: Sensitive values stored as environment variables, never in config files  
3. **Database Performance**: Connection pooling configured for concurrent operations
4. **API Design**: RESTful endpoints following OpenAPI 3.0 standards
5. **Cost Management**: Real-time tracking and budget enforcement for AI API usage
6. **Quality Assurance**: 417 automated tests with comprehensive coverage
7. **CI/CD Pipeline**: Automated quality gates (formatting, linting, security, testing)
8. **Error Resilience**: Circuit breaker pattern and retry mechanisms for external API calls
9. **Async Architecture**: Full async/await support for concurrent operations
10. **Template System**: Jinja2 templates for dynamic AI prompts and documentation

## Development Workflow

### Quality Assurance Process
1. **Test-Driven Development**: Write tests first, implement features second
2. **Automated Quality Gates**: Every commit must pass all quality checks
3. **Comprehensive Testing**: Unit tests with mocked dependencies, integration tests with real services
4. **Code Review Standards**: All code changes reviewed for quality and security
5. **Continuous Integration**: Automated testing and quality checks on every pull request

### CI/CD Quality Gates
1. **Code Formatting** (Black): Ensures consistent code style
2. **Import Sorting** (isort): Maintains clean import organization
3. **Linting** (Flake8): Catches code quality issues and potential bugs
4. **Security Scanning** (Bandit): Identifies security vulnerabilities
5. **Type Checking** (MyPy): Validates type hints and catches type errors
6. **Test Execution** (Pytest): Runs full test suite with coverage reporting