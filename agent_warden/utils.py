"""
Agent Warden utility functions.

This module contains utility functions for file operations, frontmatter parsing,
timestamp formatting, and other common operations.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import yaml


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_content_checksum(content: str) -> str:
    """Calculate SHA256 checksum of string content.

    Args:
        content: String content to checksum

    Returns:
        SHA256 hex digest of the content
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content that may contain frontmatter

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    lines = content.split('\n')

    # Check if file starts with frontmatter delimiter
    if not lines or lines[0].strip() != '---':
        return {}, content

    # Find the closing delimiter
    frontmatter_lines = []
    body_start_idx = 0

    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            # Found closing delimiter
            body_start_idx = i + 1
            break
        frontmatter_lines.append(lines[i])
    else:
        # No closing delimiter found
        return {}, content

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load('\n'.join(frontmatter_lines)) or {}
    except yaml.YAMLError:
        frontmatter = {}

    # Get body content (skip leading blank lines)
    body_lines = lines[body_start_idx:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)

    return frontmatter, '\n'.join(body_lines)


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content.

    Args:
        content: Markdown content that may contain frontmatter

    Returns:
        Content with frontmatter removed
    """
    _, body = parse_frontmatter(content)
    return body


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to human-readable relative or absolute time.

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Human-readable time string like "2 hours ago" or "Jan 15, 2025 at 3:45 PM"
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        # Use same timezone as timestamp, or naive if timestamp is naive
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        diff = now - timestamp

        # For times less than 1 minute ago
        if diff.total_seconds() < 60:
            seconds = int(diff.total_seconds())
            return "just now" if seconds < 10 else f"{seconds} seconds ago"

        # For times less than 1 hour ago
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

        # For times less than 24 hours ago
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"

        # For times less than 7 days ago
        elif diff.days < 7:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"

        # For times less than 30 days ago
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

        # For older times, show absolute date
        else:
            return timestamp.strftime("%b %d, %Y at %I:%M %p")

    except (ValueError, AttributeError):
        # If parsing fails, return the original string
        return timestamp_str


def get_file_info(file_path: Path, source_type: str = "unknown") -> Dict:
    """Get file information including checksum."""
    return {
        "checksum": calculate_file_checksum(file_path),
        "source": str(file_path),
        "source_type": source_type,
        "installed_at": datetime.now(timezone.utc).isoformat()
    }


def process_command_template(content: str, target: str, rules_dir: str) -> str:
    """Process command template by replacing placeholders with target-specific values.

    Args:
        content: Command file content with template placeholders
        target: Target assistant ('augment', 'cursor', 'claude', 'windsurf', 'codex')
        rules_dir: Path to the rules directory for this target

    Returns:
        Processed content with placeholders replaced
    """
    # Define platform-specific notes
    platform_notes = {
        'augment': """This project uses **Augment** as the AI coding assistant.
- Rules are located in `.augment/rules/`
- Commands are located in `.augment/commands/`
- Both rules and commands use Markdown format""",

        'cursor': """This project uses **Cursor** as the AI coding assistant.
- Rules are located in `.cursor/rules/`
- Cursor uses a rules-based system where all files in the rules directory are automatically loaded
- Commands are also stored in `.cursor/rules/` alongside rules""",

        'claude': """This project uses **Claude Code** as the AI coding assistant.
- Rules are located in `.claude/rules/`
- Commands are located in `.claude/commands/`
- May also reference global rules from `~/.claude/warden-rules.md`""",

        'windsurf': """This project uses **Windsurf** as the AI coding assistant.
- Rules are located in `.windsurf/rules/`
- Commands are located in `.windsurf/commands/`
- May also reference global rules from `~/.codeium/windsurf/memories/global_rules.md`""",

        'codex': """This project uses **Codex** as the AI coding assistant.
- Rules are located in `.codex/rules/`
- Commands are located in `.codex/commands/`
- Additional configuration may be in `.codex/config.toml`"""
    }

    # Replace template variables
    processed = content.replace('{{RULES_DIR}}', rules_dir)
    processed = processed.replace('{{PLATFORM_NOTES}}', platform_notes.get(target, ''))

    return processed

