"""
Core exceptions for the AI Development Automation System
"""


class BaseSystemError(Exception):
    """Base exception for all system errors"""
    pass


class PluginError(BaseSystemError):
    """Base exception for plugin-related errors"""
    pass


class PluginValidationError(PluginError):
    """Exception raised when plugin validation fails"""
    pass


class PluginConnectionError(PluginError):
    """Exception raised when plugin connection fails"""
    pass


class WorkspaceError(BaseSystemError):
    """Base exception for workspace-related errors"""
    pass


class WorkspaceCleanupError(WorkspaceError):
    """Exception raised when workspace cleanup fails"""
    pass


class WorkflowError(BaseSystemError):
    """Base exception for workflow-related errors"""
    pass


class VariableResolutionError(WorkflowError):
    """Exception raised when variable resolution fails"""
    pass


class StepExecutionError(WorkflowError):
    """Exception raised when workflow step execution fails"""
    pass


class AIProviderError(BaseSystemError):
    """Base exception for AI provider-related errors"""
    pass


class CostBudgetError(AIProviderError):
    """Exception raised when cost budget is exceeded"""
    pass


class SecurityError(BaseSystemError):
    """Exception raised for security-related issues"""
    pass


class ValidationError(BaseSystemError):
    """Exception raised for input validation failures"""
    pass