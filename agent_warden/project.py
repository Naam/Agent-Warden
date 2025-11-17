"""
Project state management for Agent Warden.

Handles project metadata, targets, and installed items tracking.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fs_backend import LocalBackend, RemoteBackend, parse_location


class ProjectState:
    """Represents the state of an installed project with support for multiple targets."""

    def __init__(self, name: str, path: str, targets: Optional[Dict] = None, timestamp: Optional[str] = None,
                 default_targets: Optional[List[str]] = None):
        """Initialize ProjectState.

        Args:
            name: Project name
            path: Project path (can be local path or remote SSH location like user@host:/path)
            targets: Dict mapping target names to their configurations
            timestamp: Timestamp
            default_targets: List of default target names for this project
        """
        self.name = name

        # Parse location to get path and backend
        self.project_path, self.backend = parse_location(path)

        # For backward compatibility, keep self.path as Path object for local paths
        if isinstance(self.backend, LocalBackend):
            self.path = Path(self.project_path).resolve()
            # For local paths, store the resolved path as location string
            self.location_string = str(self.path)
        else:
            # For remote paths, create a pseudo-Path that won't be used for file operations
            self.path = Path(self.project_path)
            # For remote paths, store the original SSH location string
            self.location_string = path

        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        # Multi-target support: targets is a dict like:
        # {
        #   'augment': {
        #     'install_type': 'copy',
        #     'has_rules': True,
        #     'has_commands': True,
        #     'installed_rules': [...],
        #     'installed_commands': [...]
        #   },
        #   'cursor': {...}
        # }
        self.targets = targets or {}

        # Default targets: when adding rules without --target, use these
        self.default_targets = default_targets or []

    def is_remote(self) -> bool:
        """Check if this project is on a remote machine."""
        return isinstance(self.backend, RemoteBackend)

    def _normalize_installed_items(self, items: List) -> List[Dict]:
        """Normalize installed items to dict format with checksums."""
        normalized = []
        for item in items:
            if isinstance(item, str):
                normalized.append({
                    "name": item,
                    "checksum": None,
                    "source": None,
                    "installed_at": self.timestamp
                })
            elif isinstance(item, dict):
                normalized.append(item)
        return normalized

    def add_target(self, target: str, install_type: str, has_rules: bool = True,
                   has_commands: bool = False, installed_rules: Optional[List] = None,
                   installed_commands: Optional[List] = None):
        """Add a new target to this project."""
        self.targets[target] = {
            'install_type': install_type,
            'has_rules': has_rules,
            'has_commands': has_commands,
            'installed_rules': self._normalize_installed_items(installed_rules or []),
            'installed_commands': self._normalize_installed_items(installed_commands or [])
        }

    def remove_target(self, target: str) -> bool:
        """Remove a target from this project. Returns True if removed, False if not found."""
        if target in self.targets:
            del self.targets[target]
            return True
        return False

    def has_target(self, target: str) -> bool:
        """Check if project has a specific target."""
        return target in self.targets

    def get_target_config(self, target: str) -> Optional[Dict]:
        """Get configuration for a specific target."""
        return self.targets.get(target)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'path': self.location_string,  # Save original location string (local or remote)
            'timestamp': self.timestamp,
            'targets': self.targets,
            'default_targets': self.default_targets
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectState':
        """Create ProjectState from dictionary.

        Handles old single-target format by converting to new multi-target format.
        """
        # New format with 'targets' key
        if 'targets' in data:
            return cls(
                name=data['name'],
                path=data['path'],
                timestamp=data.get('timestamp'),
                targets=data['targets'],
                default_targets=data.get('default_targets', [])
            )

        # Old format with single 'target' key - convert to new format
        target_name = data.get('target')
        if target_name:
            # Normalize installed items
            def normalize_items(items):
                normalized = []
                for item in (items or []):
                    if isinstance(item, str):
                        normalized.append({
                            "name": item,
                            "checksum": None,
                            "source": None,
                            "installed_at": data.get('timestamp', datetime.now(timezone.utc).isoformat())
                        })
                    elif isinstance(item, dict):
                        normalized.append(item)
                return normalized

            targets = {
                target_name: {
                    'install_type': data.get('install_type', 'copy'),
                    'has_rules': data.get('has_rules', True),
                    'has_commands': data.get('has_commands', False),
                    'installed_rules': normalize_items(data.get('installed_rules', [])),
                    'installed_commands': normalize_items(data.get('installed_commands', []))
                }
            }
            return cls(
                name=data['name'],
                path=data['path'],
                timestamp=data.get('timestamp'),
                targets=targets
            )

        # Empty project
        return cls(name=data['name'], path=data['path'], timestamp=data.get('timestamp'))

    def get_rules_destination_path(self, config, target: str) -> Path:
        """Get the full destination path for rules directory.

        Args:
            config: WardenConfig instance
            target: Target to get path for
        """
        target_rules_path = config.get_target_rules_path(target)
        return self.path / target_rules_path

    def get_commands_destination_path(self, config, target: str) -> Path:
        """Get the full destination path for commands directory.

        Args:
            config: WardenConfig instance
            target: Target to get path for
        """
        target_commands_path = config.get_target_commands_path(target)
        return self.path / target_commands_path

