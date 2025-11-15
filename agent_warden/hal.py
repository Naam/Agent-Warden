"""
Agent Warden Hardware Abstraction Layer (HAL).

This module provides the HAL for converting rules between different AI coding
agent formats. It supports Cursor, Augment, Claude Code, Windsurf, and Codex.
"""

from typing import Dict, List, Optional

import yaml

from .utils import parse_frontmatter


class AgentConverter:
    """Base class for agent-specific rule format converters."""

    # Official documentation URL for this agent's rules format
    DOCS_URL: Optional[str] = None

    # Supported frontmatter fields for this agent
    SUPPORTED_FIELDS: List[str] = []

    def __init__(self):
        """Initialize the converter."""
        pass

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Convert rule content to agent-specific format.

        Args:
            content: Original rule content
            frontmatter: Parsed frontmatter dictionary
            body: Rule body content (without frontmatter)

        Returns:
            Converted content for the target agent
        """
        raise NotImplementedError("Subclasses must implement convert()")


class CursorConverter(AgentConverter):
    """Converter for Cursor AI coding assistant.

    Official Documentation: https://cursor.com/docs/context/rules

    Cursor uses YAML frontmatter with the following fields:
    - description: Description of the rule
    - globs: File patterns to apply the rule to
    - alwaysApply: Whether to always apply this rule
    """

    DOCS_URL = "https://cursor.com/docs/context/rules"
    SUPPORTED_FIELDS = ['description', 'globs', 'alwaysApply']

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Convert to Cursor format with supported frontmatter fields."""
        cursor_frontmatter = {}

        # Only include supported fields
        for field in self.SUPPORTED_FIELDS:
            if field in frontmatter:
                cursor_frontmatter[field] = frontmatter[field]

        # Reconstruct with Cursor frontmatter
        if cursor_frontmatter:
            yaml_str = yaml.dump(cursor_frontmatter, default_flow_style=False, sort_keys=False)
            return f"---\n{yaml_str}---\n\n{body}"
        else:
            return body


class AugmentConverter(AgentConverter):
    """Converter for Augment Code AI assistant.

    Official Documentation: https://docs.augmentcode.com/cli/rules

    Augment uses YAML frontmatter with the following fields:
    - description: Description of the rule
    - globs: File patterns to apply the rule to
    - alwaysApply: Whether to always apply this rule
    - type: Type of rule (e.g., 'rule', 'command')
    """

    DOCS_URL = "https://docs.augmentcode.com/cli/rules"
    SUPPORTED_FIELDS = ['description', 'globs', 'alwaysApply', 'type']

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Keep as-is (this is the canonical format)."""
        return content


class ClaudeConverter(AgentConverter):
    """Converter for Claude Code CLI.

    Official Documentation: https://www.anthropic.com/engineering/claude-code-best-practices

    Claude Code CLI uses plain markdown without frontmatter.
    Rules are stored in ~/.claude/rules/ or project .claude/rules/
    The primary configuration file is CLAUDE.md which is automatically pulled into context.
    """

    DOCS_URL = "https://www.anthropic.com/engineering/claude-code-best-practices"
    SUPPORTED_FIELDS = []

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Strip frontmatter completely, return plain markdown."""
        return body


class WindsurfConverter(AgentConverter):
    """Converter for Windsurf AI assistant.

    Windsurf uses a format similar to Augment.
    Global rules are stored in ~/.codeium/windsurf/memories/global_rules.md
    """

    DOCS_URL = None  # Windsurf doesn't have public docs for rules format yet
    SUPPORTED_FIELDS = ['description', 'globs', 'alwaysApply', 'type']

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Use Augment format for now."""
        return content


class CodexConverter(AgentConverter):
    """Converter for Codex AI assistant.

    Codex uses a format similar to Augment.
    """

    DOCS_URL = None  # Codex doesn't have public docs for rules format yet
    SUPPORTED_FIELDS = ['description', 'globs', 'alwaysApply', 'type']

    def convert(self, content: str, frontmatter: dict, body: str) -> str:
        """Use Augment format for now."""
        return content


class AgentHAL:
    """Hardware Abstraction Layer (HAL) for AI coding agent rule formats.

    This class provides a unified interface for converting rules from the canonical
    Augment format to target-specific formats for different AI coding assistants.

    Supported Agents:
    - Cursor: https://cursor.com/docs/context/rules
    - Augment Code: https://docs.augmentcode.com/cli/rules
    - Claude Code CLI
    - Windsurf
    - Codex
    """

    def __init__(self):
        """Initialize the HAL with agent-specific converters."""
        self._converters: Dict[str, AgentConverter] = {
            'cursor': CursorConverter(),
            'augment': AugmentConverter(),
            'claude': ClaudeConverter(),
            'windsurf': WindsurfConverter(),
            'codex': CodexConverter(),
        }

    def get_converter(self, target: str) -> AgentConverter:
        """Get the converter for a specific target agent.

        Args:
            target: Target agent name

        Returns:
            AgentConverter instance for the target
        """
        return self._converters.get(target, AugmentConverter())

    def convert(self, content: str, target: str) -> str:
        """Convert rule content to target-specific format.

        Args:
            content: Rule content in canonical Augment format
            target: Target assistant ('claude', 'augment', 'cursor', 'windsurf', 'codex')

        Returns:
            Converted content for the target assistant
        """
        frontmatter, body = parse_frontmatter(content)
        converter = self.get_converter(target)
        return converter.convert(content, frontmatter, body)

    def get_docs_url(self, target: str) -> Optional[str]:
        """Get the official documentation URL for a target agent's rules format.

        Args:
            target: Target agent name

        Returns:
            Documentation URL or None if not available
        """
        converter = self.get_converter(target)
        return converter.DOCS_URL

    def get_supported_fields(self, target: str) -> List[str]:
        """Get the list of supported frontmatter fields for a target agent.

        Args:
            target: Target agent name

        Returns:
            List of supported field names
        """
        converter = self.get_converter(target)
        return converter.SUPPORTED_FIELDS


# Global HAL instance
_hal_instance = None


def get_hal() -> AgentHAL:
    """Get the global HAL instance (singleton pattern)."""
    global _hal_instance
    if _hal_instance is None:
        _hal_instance = AgentHAL()
    return _hal_instance


def convert_rule_format(content: str, target: str) -> str:
    """Convert rule format for specific target assistant.

    This is a compatibility wrapper for the AgentHAL class.

    Args:
        content: Rule content in canonical Augment format
        target: Target assistant ('claude', 'augment', 'cursor', 'windsurf', 'codex')

    Returns:
        Converted content for the target assistant
    """
    return get_hal().convert(content, target)

