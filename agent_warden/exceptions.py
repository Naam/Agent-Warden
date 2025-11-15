"""
Agent Warden exceptions.

This module contains all custom exception classes used throughout Agent Warden.
"""


class WardenError(Exception):
    """Base exception for Agent Warden errors."""
    pass


class ProjectNotFoundError(WardenError):
    """Raised when a project is not found."""
    pass


class ProjectAlreadyExistsError(WardenError):
    """Raised when trying to install a project that already exists."""
    pass


class InvalidTargetError(WardenError):
    """Raised when an invalid target is specified."""
    pass


class FileOperationError(WardenError):
    """Raised when file operations fail."""
    pass

