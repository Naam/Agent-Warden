"""
Agent Warden - Centralized Rules & Commands Manager for AI Coding Assistants.

This package provides tools to manage and synchronize rules and commands across
multiple AI coding assistants including Cursor, Augment, Claude Code, Windsurf, and Codex.
"""

__version__ = "1.0.0"

# Import exceptions
from .exceptions import (
    FileOperationError,
    InvalidTargetError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
)

# Import HAL
from .hal import (
    AgentConverter,
    AgentHAL,
    AugmentConverter,
    ClaudeConverter,
    CodexConverter,
    CursorConverter,
    WindsurfConverter,
    convert_rule_format,
    get_hal,
)

# Import utilities
from .utils import (
    calculate_file_checksum,
    format_timestamp,
    get_file_info,
    parse_frontmatter,
    process_command_template,
    strip_frontmatter,
)

__all__ = [
    # Version
    "__version__",
    # Exceptions
    "WardenError",
    "ProjectNotFoundError",
    "ProjectAlreadyExistsError",
    "InvalidTargetError",
    "FileOperationError",
    # Utilities
    "calculate_file_checksum",
    "parse_frontmatter",
    "strip_frontmatter",
    "format_timestamp",
    "get_file_info",
    "process_command_template",
    # HAL
    "AgentConverter",
    "CursorConverter",
    "AugmentConverter",
    "ClaudeConverter",
    "WindsurfConverter",
    "CodexConverter",
    "AgentHAL",
    "get_hal",
    "convert_rule_format",
]
