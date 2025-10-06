"""
Core exceptions for the AI Development Automation System
"""


class BaseSystemError(Exception):
    """Base exception for system-related errors"""
    pass


class SecurityError(BaseSystemError):
    """Exception raised for security-related issues"""
    pass


class ValidationError(BaseSystemError):
    """Exception raised for input validation failures"""
    pass


class PluginError(BaseSystemError):
    """Base exception for plugin-related errors"""
    pass
