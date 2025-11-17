"""
Configuration management for Agent Warden.

Handles loading, saving, and accessing configuration, state, and registry data.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class WardenConfig:
    """Configuration management for Agent Warden targets and paths."""

    # Default target configurations with rules and commands paths
    TARGET_CONFIGS = {
        'cursor': {
            'rules_path': '.cursor/rules/',
            'commands_path': '.cursor/rules/',
            'supports_commands': False,
            'global_config': None
        },
        'augment': {
            'rules_path': '.augment/rules/',
            'commands_path': '.augment/commands/',
            'supports_commands': True,
            'global_config': None
        },
        'claude': {
            'rules_path': '.claude/rules/',
            'commands_path': '.claude/commands/',
            'supports_commands': True,
            'global_config': 'CLAUDE.md'
        },
        'windsurf': {
            'rules_path': '.windsurf/rules/',
            'commands_path': '.windsurf/commands/',
            'supports_commands': False,
            'global_config': 'global_rules.md'
        },
        'codex': {
            'rules_path': '.codex/rules/',
            'commands_path': '.codex/commands/',
            'supports_commands': True,
            'global_config': 'config.toml'
        }
    }

    DEFAULT_TARGET = 'augment'
    CONFIG_FILE = '.warden_config.json'
    STATE_FILE = '.warden_state.json'
    RULES_DIR = 'rules'
    COMMANDS_DIR = 'commands'
    PACKAGES_DIR = 'packages'
    REGISTRY_FILE = '.registry.json'

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()
        self.config_path = self.base_path / self.CONFIG_FILE
        self.state_path = self.base_path / self.STATE_FILE
        self.rules_dir = self.base_path / self.RULES_DIR
        self.commands_path = self.base_path / self.COMMANDS_DIR
        self.packages_path = self.base_path / self.PACKAGES_DIR
        self.registry_path = self.packages_path / self.REGISTRY_FILE

        self.config = self._load_config()
        self.state = self._load_state()
        self.registry = self._load_registry()

        self.commands_path.mkdir(exist_ok=True)
        self.packages_path.mkdir(exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                    # Add default values for new config options if missing
                    if 'update_remote_projects' not in config:
                        config['update_remote_projects'] = True
                    if 'auto_update' not in config:
                        config['auto_update'] = True
                    return config
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load config file: {e}")

        # Return default configuration
        return {
            'targets': self.TARGET_CONFIGS.copy(),
            'default_target': self.DEFAULT_TARGET,
            'update_remote_projects': True,
            'auto_update': True
        }

    def _load_state(self) -> Dict:
        """Load state from file or create empty state."""
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load state file: {e}")

        return {'projects': {}}

    def _load_registry(self) -> Dict:
        """Load package registry from file or create empty registry."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load registry file: {e}")

        return {'packages': {}, 'last_update_check': None}

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not save config file: {e}") from e

    def save_state(self):
        """Save current state to file."""
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not save state file: {e}") from e

    def save_registry(self):
        """Save current registry to file."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not save registry file: {e}") from e

    def get_target_config(self, target: str) -> Dict:
        """Get the full configuration for a target."""
        return self.config['targets'].get(target, self.config['targets'][self.DEFAULT_TARGET])

    def get_target_rules_path(self, target: str) -> str:
        """Get the rules path for a target."""
        target_config = self.get_target_config(target)
        if isinstance(target_config, dict):
            return target_config['rules_path']
        return target_config  # Backward compatibility

    def get_target_commands_path(self, target: str) -> str:
        """Get the commands path for a target."""
        target_config = self.get_target_config(target)
        if isinstance(target_config, dict):
            return target_config['commands_path']
        return target_config  # Fallback to rules path

    def target_supports_commands(self, target: str) -> bool:
        """Check if target supports custom commands."""
        target_config = self.get_target_config(target)
        if isinstance(target_config, dict):
            return target_config.get('supports_commands', False)
        return False

    def get_global_config_path(self, target: str) -> Optional[Path]:
        """Get the global configuration path for a target."""
        target_config = self.get_target_config(target)
        if isinstance(target_config, dict) and target_config.get('global_config'):
            return self._get_system_config_path(target, target_config['global_config'])
        return None

    def _get_system_config_path(self, target: str, config_file: str) -> Path:
        """Get system-wide configuration path based on platform."""
        home = Path.home()

        if target == 'claude':
            return home / '.claude' / config_file
        elif target == 'windsurf':
            return home / '.codeium' / 'windsurf' / 'memories' / config_file
        elif target == 'codex':
            return home / '.codex' / config_file
        else:
            return home / f'.{target}' / config_file

    def add_target(self, name: str, path: str):
        """Add a new target configuration."""
        self.config['targets'][name] = path
        self.save_config()

    def get_available_targets(self) -> List[str]:
        """Get list of available target names."""
        return list(self.config['targets'].keys())

