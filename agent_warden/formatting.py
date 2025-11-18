"""
Output formatting utilities for Agent Warden.

Provides color codes and formatting functions for terminal output.
"""

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from agent_warden.project import ProjectState


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


def format_project_info(project: 'ProjectState', verbose: bool = False) -> str:
    """Format project information for display.

    Args:
        project: ProjectState instance
        verbose: If True, show detailed target information

    Returns:
        Formatted project information string
    """
    from agent_warden.utils import format_timestamp

    target_names = list(project.targets.keys())
    targets_str = ', '.join(target_names) if target_names else 'none'

    # Show remote location if project is on remote server
    if project.is_remote():
        path_display = project.location_string
        remote_icon = "🌐"
    else:
        path_display = str(project.path)
        remote_icon = ""

    info = (f"📦 {project.name}\n"
            f"   {remote_icon} Path: {path_display}\n"
            f"   Targets: {targets_str}")

    if verbose:
        for target_name, target_config in project.targets.items():
            status_icon = "🔗" if target_config['install_type'] == 'symlink' else "📁"
            info += f"\n   {status_icon} {target_name}:"
            info += f"\n      Type: {target_config['install_type']}"
            info += f"\n      Rules: {'✓' if target_config.get('has_rules') else '✗'}"
            info += f"\n      Commands: {'✓' if target_config.get('has_commands') else '✗'}"

            if target_config.get('has_commands') and target_config.get('installed_commands'):
                cmd_names = [c['name'] if isinstance(c, dict) else c for c in target_config['installed_commands']]
                info += f"\n      Installed Commands: {', '.join(cmd_names)}"

    info += f"\n   Updated: {format_timestamp(project.timestamp)}"
    return info


def format_project_detailed(project: 'ProjectState', manager) -> str:
    """Format detailed project information with status of installed items.

    Args:
        project: ProjectState instance
        manager: WardenManager instance

    Returns:
        Formatted detailed project information string
    """
    from agent_warden.utils import format_timestamp

    target_names = list(project.targets.keys())
    targets_str = ', '.join(target_names) if target_names else 'none'

    # Show remote location if project is on remote server
    if project.is_remote():
        path_display = project.location_string
        remote_icon = "🌐"
    else:
        path_display = str(project.path)
        remote_icon = ""

    info = (f"📦 {project.name}\n"
            f"   {remote_icon} Path: {path_display}\n"
            f"   Targets: {targets_str}\n")

    if project.default_targets:
        info += f"   Default Targets: {', '.join(project.default_targets)}\n"

    info += f"   Updated: {format_timestamp(project.timestamp)}\n"

    # Get status for the project
    try:
        status = manager.check_project_status(project.name)

        # Display each target
        for target_name, target_config in project.targets.items():
            status_icon = "🔗" if target_config['install_type'] == 'symlink' else "📁"
            info += f"\n   {status_icon} {target_name} ({target_config['install_type']}):\n"

            # Display rules
            if target_config.get('has_rules') and target_config.get('installed_rules'):
                info += f"      Rules ({len(target_config['installed_rules'])}):\n"
                # Find max rule name length for alignment
                rule_names = [r['name'] if isinstance(r, dict) else r for r in target_config['installed_rules']]
                max_rule_len = max(len(name) for name in rule_names) if rule_names else 0

                for rule_info in target_config['installed_rules']:
                    rule_name = rule_info['name'] if isinstance(rule_info, dict) else rule_info
                    rule_status = get_item_status(rule_name, 'rule', status)
                    info += f"         • {rule_name:<{max_rule_len}} {rule_status}\n"

            # Display commands
            if target_config.get('has_commands') and target_config.get('installed_commands'):
                info += f"      Commands ({len(target_config['installed_commands'])}):\n"
                # Find max command name length for alignment
                cmd_names = [c['name'] if isinstance(c, dict) else c for c in target_config['installed_commands']]
                max_cmd_len = max(len(name) for name in cmd_names) if cmd_names else 0

                for cmd_info in target_config['installed_commands']:
                    cmd_name = cmd_info['name'] if isinstance(cmd_info, dict) else cmd_info
                    cmd_status = get_item_status(cmd_name, 'command', status)
                    info += f"         • {cmd_name:<{max_cmd_len}} {cmd_status}\n"
    except Exception as e:
        info += f"\n   [WARNING] Could not retrieve status: {e}\n"

    return info


def get_item_status(item_name: str, item_type: str, status: Dict) -> str:
    """Get status indicator for an item with color.

    Args:
        item_name: Name of the item (rule or command)
        item_type: Type of item ('rule' or 'command')
        status: Status dictionary from check_project_status

    Returns:
        Colored status string
    """
    # Check if item is in any status category
    if item_type == 'rule':
        if any(r['name'] == item_name for r in status.get('conflict_rules', [])):
            return colored_status('CONFLICT')
        if any(r['name'] == item_name for r in status.get('user_modified_rules', [])):
            return colored_status('MODIFIED')
        if any(r['name'] == item_name for r in status.get('outdated_rules', [])):
            return colored_status('OUTDATED')
        if any(r['name'] == item_name for r in status.get('missing_sources', []) if r.get('type') == 'rule'):
            return colored_status('MISSING SOURCE')
        if any(r['name'] == item_name for r in status.get('missing_installed', []) if r.get('type') == 'rule'):
            return colored_status('MISSING FILE')
    else:  # command
        if any(c['name'] == item_name for c in status.get('conflict_commands', [])):
            return colored_status('CONFLICT')
        if any(c['name'] == item_name for c in status.get('user_modified_commands', [])):
            return colored_status('MODIFIED')
        if any(c['name'] == item_name for c in status.get('outdated_commands', [])):
            return colored_status('OUTDATED')
        if any(c['name'] == item_name for c in status.get('missing_sources', []) if c.get('type') == 'command'):
            return colored_status('MISSING SOURCE')
        if any(c['name'] == item_name for c in status.get('missing_installed', []) if c.get('type') == 'command'):
            return colored_status('MISSING FILE')

    return colored_status('UP TO DATE')

