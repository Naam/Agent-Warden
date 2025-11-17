"""
Output formatting utilities for Agent Warden.

Provides color codes and formatting functions for terminal output.
"""


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Wrap text in color codes."""
        return f"{color}{text}{Colors.NC}"


def colored_status(status_type: str, message: str = "") -> str:
    """Return a colored status message.

    Args:
        status_type: Type of status (SUCCESS, ERROR, WARNING, INFO, etc.)
        message: Optional message to append after the status

    Returns:
        Colored status string
    """
    color_map = {
        'SUCCESS': Colors.GREEN,
        'ERROR': Colors.RED,
        'WARNING': Colors.YELLOW,
        'INFO': Colors.BLUE,
        'UPDATE': Colors.CYAN,
        'MODIFIED': Colors.YELLOW,
        'CONFLICT': Colors.RED,
        'OUTDATED': Colors.YELLOW,
        'UP TO DATE': Colors.GREEN,
        'MISSING SOURCE': Colors.RED,
        'MISSING FILE': Colors.RED,
        'TIP': Colors.CYAN,
        'CHECK': Colors.BLUE,
        'CELEBRATE': Colors.MAGENTA,
        'PACKAGE': Colors.BLUE,
    }

    color = color_map.get(status_type, Colors.NC)
    status_text = Colors.colorize(f"[{status_type}]", color)

    if message:
        return f"{status_text} {message}"
    return status_text

