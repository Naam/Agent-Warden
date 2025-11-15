#!/usr/bin/env python3
"""
Agent Warden - Manage and synchronize agentic AI tool configurations across multiple projects.

This script provides comprehensive functionality to install, update, and manage
both MDC rules and custom commands across different AI development tools with
support for symlinks, copies, and system-wide configurations.
"""

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Import from agent_warden package
from agent_warden.exceptions import (
    FileOperationError,
    InvalidTargetError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
)
from agent_warden.hal import (
    convert_rule_format,
)
from agent_warden.utils import (
    calculate_file_checksum,
    format_timestamp,
    process_command_template,
)
from fs_backend import (
    BackendError,
    FileSystemBackend,
    LocalBackend,
    RemoteBackend,
    RemoteOperationError,
    RemotePathError,
    RemotePermissionError,
    SSHConnectionError,
    parse_location,
)


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
            'update_remote_projects': True,  # Include remote projects in global updates by default
            'auto_update': True  # Enable automatic updates by default
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
            # Claude Code CLI uses ~/.claude/ directory
            return home / '.claude' / config_file
        elif target == 'windsurf':
            return home / '.codeium' / 'windsurf' / 'memories' / config_file
        elif target == 'codex':
            return home / '.codex' / config_file
        else:
            # Generic approach
            return home / f'.{target}' / config_file

    def add_target(self, name: str, path: str):
        """Add a new target configuration."""
        self.config['targets'][name] = path
        self.save_config()

    def get_available_targets(self) -> List[str]:
        """Get list of available target names."""
        return list(self.config['targets'].keys())


class GitHubPackage:
    """Represents a GitHub package with version information."""

    def __init__(self, owner: str, repo: str, ref: str = "main",
                 installed_ref: Optional[str] = None, installed_at: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.ref = ref  # Target ref (branch/tag)
        self.installed_ref = installed_ref  # Currently installed ref
        self.installed_at = installed_at or datetime.now(timezone.utc).isoformat()
        self.name = f"{owner}/{repo}"

    @property
    def directory_name(self) -> str:
        """Get the directory name for this package."""
        return f"{self.owner}-{self.repo}"

    @property
    def github_url(self) -> str:
        """Get the GitHub URL for this package."""
        return f"https://github.com/{self.owner}/{self.repo}.git"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'owner': self.owner,
            'repo': self.repo,
            'ref': self.ref,
            'installed_ref': self.installed_ref,
            'installed_at': self.installed_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GitHubPackage':
        """Create GitHubPackage from dictionary."""
        return cls(
            owner=data['owner'],
            repo=data['repo'],
            ref=data.get('ref', 'main'),
            installed_ref=data.get('installed_ref'),
            installed_at=data.get('installed_at')
        )

    @classmethod
    def from_spec(cls, spec: str) -> 'GitHubPackage':
        """Create GitHubPackage from spec string like 'owner/repo' or 'owner/repo@ref'."""
        if '@' in spec:
            repo_part, ref = spec.split('@', 1)
        else:
            repo_part, ref = spec, 'main'

        if '/' not in repo_part:
            raise ValueError(f"Invalid package spec: {spec}. Expected format: owner/repo[@ref]")

        owner, repo = repo_part.split('/', 1)
        return cls(owner, repo, ref)


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

    def get_rules_destination_path(self, config: WardenConfig, target: str) -> Path:
        """Get the full destination path for rules directory.

        Args:
            config: WardenConfig instance
            target: Target to get path for
        """
        target_rules_path = config.get_target_rules_path(target)
        return self.path / target_rules_path

    def get_commands_destination_path(self, config: WardenConfig, target: str) -> Path:
        """Get the full destination path for commands directory.

        Args:
            config: WardenConfig instance
            target: Target to get path for
        """
        target_commands_path = config.get_target_commands_path(target)
        return self.path / target_commands_path


class WardenManager:
    """Main manager class for Agent Warden operations."""

    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        if base_path is None:
            # Always use the directory where warden.py is located
            # This ensures state, config, packages, rules, and commands are all
            # in the agent-warden installation directory
            base_path = Path(__file__).parent.resolve()

        self.config = WardenConfig(base_path)

        # Ensure rules directory exists
        if not self.config.rules_dir.exists():
            raise FileNotFoundError(f"Rules directory not found: {self.config.rules_dir}")

    def _validate_project_location(self, location: Union[str, Path]) -> Tuple[str, str, FileSystemBackend]:
        """Validate and resolve project location (local or remote).

        Returns:
            Tuple of (location_string, project_path, backend)
        """
        location_str = str(location)

        try:
            project_path, backend = parse_location(location_str)
        except Exception as e:
            raise WardenError(f"Invalid project location '{location_str}': {e}") from e

        # Validate that the path exists and is a directory
        try:
            if not backend.exists(project_path):
                raise WardenError(f"Project path does not exist: {location_str}")

            if not backend.is_dir(project_path):
                raise WardenError(f"Project path is not a directory: {location_str}")
        except (SSHConnectionError, RemotePermissionError, RemotePathError) as e:
            raise WardenError(f"Cannot access remote location '{location_str}': {e}") from e
        except BackendError as e:
            raise WardenError(f"Backend error for '{location_str}': {e}") from e
        except WardenError:
            # Re-raise WardenError as-is
            raise

        # For local paths, return the resolved path as location_string for consistency
        # For remote paths, return the original SSH location string
        if isinstance(backend, LocalBackend):
            resolved_location = str(Path(project_path).resolve())
            return resolved_location, project_path, backend
        else:
            return location_str, project_path, backend

    def _get_project_name(self, project_path: str, backend: FileSystemBackend) -> str:
        """Generate project name from path.

        Args:
            project_path: The project path (without host info for remote)
            backend: The backend instance
        """
        # Extract the last component of the path
        return Path(project_path).name

    def _create_target_directory(self, destination_path: Path):
        """Create target directory if it doesn't exist."""
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise FileOperationError(f"Could not create target directory {destination_path.parent}: {e}") from e

    def _get_available_commands(self) -> List[str]:
        """Get list of available command files from built-in and packages."""
        commands = []

        # Built-in commands
        # Exclude the specific commands/example/ directory (shipped examples)
        if self.config.commands_path.exists():
            example_dir = self.config.commands_path / 'example'
            for file_path in self.config.commands_path.rglob('*.md'):
                # Skip files in the specific commands/example/ directory
                try:
                    file_path.relative_to(example_dir)
                    continue  # File is in example/ directory, skip it
                except ValueError:
                    # File is not in example/ directory, include it
                    rel_path = file_path.relative_to(self.config.commands_path)
                    command_name = str(rel_path.with_suffix(''))
                    commands.append(command_name)

        # Package commands
        for package_name, package_data in self.config.registry['packages'].items():
            if 'content' in package_data and 'commands' in package_data['content']:
                for cmd in package_data['content']['commands']:
                    commands.append(f"{package_name}:{cmd}")

        return sorted(commands)

    def _get_available_rules(self) -> List[str]:
        """Get list of available rule files from built-in rules directory and packages."""
        rules = []

        # Built-in rules (from rules/ directory, not mdc.md)
        # Exclude the specific rules/example/ directory (shipped examples)
        rules_path = self.config.base_path / 'rules'
        if rules_path.exists():
            example_dir = rules_path / 'example'
            for file_path in rules_path.rglob('*.md'):
                # Skip files in the specific rules/example/ directory
                try:
                    file_path.relative_to(example_dir)
                    continue  # File is in example/ directory, skip it
                except ValueError:
                    # File is not in example/ directory, include it
                    rel_path = file_path.relative_to(rules_path)
                    rule_name = str(rel_path.with_suffix(''))
                    rules.append(rule_name)

        # Package rules
        for package_name, package_data in self.config.registry['packages'].items():
            if 'content' in package_data and 'rules' in package_data['content']:
                for rule in package_data['content']['rules']:
                    rules.append(f"{package_name}:{rule}")

        return sorted(rules)

    def _resolve_command_path(self, command_spec: str) -> Tuple[Path, str]:
        """Resolve command specification to actual file path and source."""
        if ':' in command_spec:
            # Package command: package_name:command_name
            package_name, command_name = command_spec.split(':', 1)

            if package_name not in self.config.registry['packages']:
                raise FileNotFoundError(f"Package '{package_name}' not found")

            package_data = self.config.registry['packages'][package_name]
            package = GitHubPackage.from_dict(package_data)
            package_dir = self.config.packages_path / package.directory_name

            # Try multiple possible command directories
            possible_commands_dirs = ['commands', 'commands-mdc', 'mdc-commands', 'cursor-commands']
            for dir_name in possible_commands_dirs:
                command_path = package_dir / dir_name / f"{command_name}.md"
                if command_path.exists():
                    return command_path, f"package:{package_name}"

            raise FileNotFoundError(f"Command '{command_name}' not found in package '{package_name}'")
        else:
            # Try built-in command first
            command_path = self.config.commands_path / f"{command_spec}.md"
            if command_path.exists():
                return command_path, "built-in"

            # Try built-in rule (from rules/ directory)
            rules_path = self.config.base_path / 'rules' / f"{command_spec}.md"
            if rules_path.exists():
                return rules_path, "built-in-rule"

            raise FileNotFoundError(f"Built-in command or rule '{command_spec}' not found")

    def _resolve_rule_path(self, rule_spec: str) -> Tuple[Path, str]:
        """Resolve rule specification to actual file path and source."""
        if ':' in rule_spec:
            # Package rule: package_name:rule_name
            package_name, rule_name = rule_spec.split(':', 1)

            if package_name not in self.config.registry['packages']:
                raise FileNotFoundError(f"Package '{package_name}' not found")

            package_data = self.config.registry['packages'][package_name]
            package = GitHubPackage.from_dict(package_data)
            package_dir = self.config.packages_path / package.directory_name

            # Look for rule in package's rules directory
            rule_path = package_dir / 'rules' / f"{rule_name}.md"
            if rule_path.exists():
                return rule_path, f"package:{package_name}"

            raise FileNotFoundError(f"Rule '{rule_name}' not found in package '{package_name}' (expected in rules/ directory)")
        else:
            raise FileNotFoundError("No built-in rules available for installation. Use package rules instead.")

    def search_packages(self, query: str) -> Dict[str, List[str]]:
        """Search for rules and commands across all packages."""
        results = {'rules': [], 'commands': []}

        query_lower = query.lower()

        # Search built-in rules
        for rule in self._get_available_rules():
            if ':' not in rule and query_lower in rule.lower():
                results['rules'].append(rule)

        # Search built-in commands
        for cmd in self._get_available_commands():
            if ':' not in cmd and query_lower in cmd.lower():
                results['commands'].append(cmd)

        # Search package content
        for package_name, package_data in self.config.registry['packages'].items():
            if 'content' not in package_data:
                continue

            content = package_data['content']

            # Search rules
            for rule in content.get('rules', []):
                if query_lower in rule.lower():
                    results['rules'].append(f"{package_name}:{rule}")

            # Search commands
            for cmd in content.get('commands', []):
                if query_lower in cmd.lower():
                    results['commands'].append(f"{package_name}:{cmd}")

        return results

    def _get_available_packages(self) -> List[str]:
        """Get list of available packages from registry."""
        return list(self.config.registry['packages'].keys())

    def _discover_package_content(self, package_path: Path) -> Dict:
        """Discover rules and commands in a package directory."""
        content = {'rules': [], 'commands': []}

        # Discover rules in rules/ directory
        rules_dir = package_path / 'rules'
        if rules_dir.exists():
            for rule_file in rules_dir.rglob('*.md'):
                rel_path = rule_file.relative_to(rules_dir)
                rule_name = str(rel_path.with_suffix(''))

                # Skip meta-rules
                if rule_name.lower() in ['mdc', 'meta', 'format', 'template']:
                    continue

                content['rules'].append(rule_name)

        # Discover commands in commands/ directory
        commands_dir = package_path / 'commands'
        if commands_dir.exists():
            for cmd_file in commands_dir.rglob('*.md'):
                rel_path = cmd_file.relative_to(commands_dir)
                content['commands'].append(str(rel_path.with_suffix('')))

        return content

    def _run_git_command(self, args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Git command timed out"
        except FileNotFoundError:
            return 1, "", "Git not found. Please install git."

    def _install_command(self, command_spec: str, destination_dir: Path, use_copy: bool, target: str = None) -> Dict:
        """Install a specific command or rule to the destination (local only). Returns installation info with checksum."""
        try:
            source_path, source_type = self._resolve_command_path(command_spec)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Command '{command_spec}' not found: {e}") from e

        if ':' in command_spec:
            _, command_name = command_spec.split(':', 1)
        else:
            command_name = command_spec

        # All rule files are now .md
        dest_filename = f"{command_name}.md"

        dest_path = destination_dir / dest_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        checksum = calculate_file_checksum(source_path)

        # Determine if this is a command file (vs a rule file)
        is_command = '/commands/' in str(destination_dir) or str(destination_dir).endswith('/commands')

        # Process template if copying a command file with a target specified
        if use_copy and is_command and target:
            content = source_path.read_text()
            rules_dir = self.config.get_target_rules_path(target)
            processed_content = process_command_template(content, target, rules_dir)
            dest_path.write_text(processed_content)
        elif use_copy:
            self._copy_file(source_path, dest_path)
        else:
            self._create_symlink(source_path, dest_path)

        return {
            "name": command_spec,
            "checksum": checksum,
            "source": str(source_path),
            "source_type": source_type,
            "installed_at": datetime.now(timezone.utc).isoformat()
        }

    def _install_command_with_backend(self, command_spec: str, destination_dir: str,
                                     backend: FileSystemBackend, use_copy: bool, target: str = None) -> Dict:
        """Install a specific command or rule using backend. Returns installation info with checksum.

        Args:
            command_spec: Command specification (e.g., 'coding-no-emoji' or 'owner/repo:rule-name')
            destination_dir: Destination directory path (relative to backend's base)
            backend: Backend to use for installation
            use_copy: Whether to use copy mode
            target: Target assistant (e.g., 'claude', 'augment', 'cursor')
        """
        try:
            source_path, source_type = self._resolve_command_path(command_spec)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Command '{command_spec}' not found: {e}") from e

        if ':' in command_spec:
            _, command_name = command_spec.split(':', 1)
        else:
            command_name = command_spec

        # All rule files are now .md
        dest_filename = f"{command_name}.md"

        # Construct destination path
        dest_path = f"{destination_dir.rstrip('/')}/{dest_filename}"

        # Ensure parent directory exists
        backend.mkdir(destination_dir, parents=True, exist_ok=True)

        # Calculate checksum from source
        checksum = calculate_file_checksum(source_path)

        # Install file using backend
        self._install_file_with_backend(source_path, dest_path, backend, use_copy, target)

        return {
            "name": command_spec,
            "checksum": checksum,
            "source": str(source_path),
            "source_type": source_type,
            "installed_at": datetime.now(timezone.utc).isoformat()
        }

    def _update_commands(self, project_state: ProjectState, use_copy: bool):
        """Update all installed commands for a project."""
        if not project_state.has_commands:
            return

        commands_destination = project_state.get_commands_destination_path(self.config)

        for command_name in project_state.installed_commands:
            dest_path = commands_destination / f"{command_name}.md"
            source_path = self.config.commands_path / f"{command_name}.md"

            if not source_path.exists():
                print(f"Warning: Command source not found: {source_path}")
                continue

            if use_copy:
                self._copy_file(source_path, dest_path)
            else:
                # For symlinks, recreate if not pointing to correct source
                if not dest_path.is_symlink() or dest_path.resolve() != source_path:
                    if dest_path.exists():
                        dest_path.unlink()
                    self._create_symlink(source_path, dest_path)

    def _create_symlink(self, source: Path, destination: Path):
        """Create a symlink from source to destination (local only)."""
        try:
            # Remove existing file/symlink if it exists
            if destination.exists() or destination.is_symlink():
                destination.unlink()

            # Create symlink
            destination.symlink_to(source)
            return True
        except OSError as e:
            raise FileOperationError(f"Failed to create symlink from {source} to {destination}: {e}") from e

    def _copy_file(self, source: Path, destination: Path):
        """Copy file from source to destination (local only)."""
        try:
            # Remove existing file if it exists
            if destination.exists():
                destination.unlink()

            # Copy file
            shutil.copy2(source, destination)
            return True
        except (OSError, shutil.Error) as e:
            raise FileOperationError(f"Failed to copy file from {source} to {destination}: {e}") from e

    def _install_file_with_backend(self, source_path: Path, dest_path: str,
                                   backend: FileSystemBackend, use_copy: bool, target: str = None):
        """Install a file using the appropriate backend.

        Args:
            source_path: Local source file path (from warden installation)
            dest_path: Destination path (relative to backend's base path)
            backend: Backend to use for installation
            use_copy: Whether to use copy mode (symlinks only for local)
            target: Target assistant (e.g., 'claude', 'augment', 'cursor')
        """
        try:
            # Determine if this is a command file (vs a rule file)
            is_command = '/commands/' in dest_path or dest_path.endswith('/commands')

            # Check if we need to process the file content
            # Process when: copying (not symlinking) and target is specified
            should_process = (
                target is not None and
                source_path.suffix == '.md' and
                (isinstance(backend, RemoteBackend) or use_copy)
            )

            if should_process:
                # Read source file
                content = source_path.read_text()

                # Process based on file type
                if is_command:
                    # For commands: process template variables
                    # Determine rules directory path for this target
                    rules_dir = self.config.get_target_rules_path(target)
                    processed_content = process_command_template(content, target, rules_dir)
                else:
                    # For rules: convert format for target
                    processed_content = convert_rule_format(content, target)

                # Write processed content to destination
                if isinstance(backend, RemoteBackend):
                    # For remote, we need to write to a temp file first
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as tmp:
                        tmp.write(processed_content)
                        tmp_path = tmp.name
                    try:
                        backend.copy_file(tmp_path, dest_path)
                    finally:
                        Path(tmp_path).unlink()
                else:
                    # For local, write directly
                    Path(dest_path).write_text(processed_content)
            elif isinstance(backend, RemoteBackend):
                # Remote always uses copy
                backend.copy_file(str(source_path), dest_path)
            elif use_copy:
                # Local copy
                backend.copy_file(str(source_path), dest_path)
            else:
                # Local symlink
                if not backend.supports_symlinks():
                    raise WardenError(f"Backend {backend.__class__.__name__} does not support symlinks")
                backend.create_symlink(str(source_path), dest_path)
        except (RemoteOperationError, BackendError) as e:
            raise FileOperationError(f"Failed to install file to {dest_path}: {e}") from e

    def _is_symlink_to_rules(self, file_path: Path) -> bool:
        """Check if file is a symlink to our rules directory or a rule file."""
        if not file_path.is_symlink():
            return False

        try:
            target = file_path.resolve()
            # Check if it points to any file in the rules directory
            return (target.parent == self.config.rules_dir or
                    str(target).startswith(str(self.config.rules_dir)))
        except OSError:
            return False

    def _convert_symlink_to_copy(self, file_path: Path):
        """Convert a symlink to a hard copy."""
        if not file_path.is_symlink():
            raise ValueError(f"File is not a symlink: {file_path}")

        # Read the content through the symlink
        try:
            content = file_path.read_text()
            # Remove the symlink
            file_path.unlink()
            # Write the content as a regular file
            file_path.write_text(content)
        except OSError as e:
            raise FileOperationError(f"Failed to convert symlink to copy: {e}") from e

    def install_project(self, project_path: Union[str, Path], target: Optional[str] = None,
                       use_copy: bool = False,
                       install_commands: bool = False, command_names: Optional[List[str]] = None,
                       rule_names: Optional[List[str]] = None, custom_name: Optional[str] = None) -> ProjectState:
        """Install MDC rules to a project. Supports multi-target installation.

        If the project path is already registered, this will add the new target to the existing project.

        Args:
            project_path: Local path or remote SSH location (user@host:/path)
            target: Target configuration (augment, cursor, etc.)
            use_copy: Use copy instead of symlink (required for remote)
            install_commands: Whether to install commands
            command_names: List of command names to install
            rule_names: List of rule names to install
            custom_name: Custom project name
        """
        # Validate and parse location (local or remote)
        location_string, parsed_path, backend = self._validate_project_location(project_path)

        # Remote locations must use copy mode
        if isinstance(backend, RemoteBackend):
            if not use_copy:
                print("[INFO] Remote locations require file copies (symlinks not supported)")
                use_copy = True

        if target is None:
            target = self.config.config['default_target']
        elif target not in self.config.get_available_targets():
            raise InvalidTargetError(f"Unknown target: {target}. Available: {self.config.get_available_targets()}")

        if target == 'augment' and not use_copy:
            use_copy = True
            print("[INFO] Augment target requires file copies (symlinks not supported)")

        # Validate command installation request
        if install_commands and not self.config.target_supports_commands(target):
            raise WardenError(f"Target '{target}' does not support custom commands")

        if install_commands and command_names is None:
            # Install all available commands
            command_names = self._get_available_commands()

        # Check if project location already exists
        existing_project_name = None
        for existing_name, existing_data in self.config.state['projects'].items():
            existing = ProjectState.from_dict(existing_data)
            if existing.location_string == location_string:
                existing_project_name = existing_name
                break

        if existing_project_name:
            # Add target to existing project
            project_state = ProjectState.from_dict(self.config.state['projects'][existing_project_name])

            if project_state.has_target(target):
                raise WardenError(
                    f"Project '{existing_project_name}' already has target '{target}' installed. "
                    f"Use 'warden install --project {existing_project_name} --rules ...' to add more rules."
                )

            print(f"[INFO] Adding target '{target}' to existing project '{existing_project_name}'")

            # Add the new target
            install_type = 'copy' if use_copy else 'symlink'
            installed_rules_list = []
            installed_commands_list = []

            # Install rules from rules/ directory or packages
            if rule_names:
                rules_destination = project_state.get_rules_destination_path(self.config, target)
                # For local: use absolute path; for remote: use path relative to remote base
                rules_dest_str = str(rules_destination)

                for rule_name in rule_names:
                    install_info = self._install_command_with_backend(rule_name, rules_dest_str, backend, use_copy, target)
                    installed_rules_list.append(install_info)

            # Install commands if requested
            if install_commands and command_names:
                commands_destination = project_state.get_commands_destination_path(self.config, target)
                # For local: use absolute path; for remote: use path relative to remote base
                commands_dest_str = str(commands_destination)

                for command_name in command_names:
                    install_info = self._install_command_with_backend(command_name, commands_dest_str, backend, use_copy, target)
                    installed_commands_list.append(install_info)

            project_state.add_target(
                target=target,
                install_type=install_type,
                has_rules=bool(rule_names),
                has_commands=install_commands,
                installed_rules=installed_rules_list,
                installed_commands=installed_commands_list
            )

            project_state.timestamp = datetime.now(timezone.utc).isoformat()
            self.config.state['projects'][existing_project_name] = project_state.to_dict()
            self.config.save_state()

            return project_state

        # New project installation
        # Use custom name if provided, otherwise derive from path
        if custom_name:
            if not custom_name.strip():
                raise WardenError("Custom project name cannot be empty")
            project_name = custom_name.strip()
        else:
            project_name = self._get_project_name(parsed_path, backend)

        if project_name in self.config.state['projects']:
            counter = 1
            while f"{project_name}_{counter}" in self.config.state['projects']:
                counter += 1
            project_name = f"{project_name}_{counter}"

        # Create project state with new multi-target format
        install_type = 'copy' if use_copy else 'symlink'
        installed_rules_list = []
        installed_commands_list = []

        # Create empty project state with location string
        project_state = ProjectState(name=project_name, path=location_string)

        # Install rules from rules/ directory or packages
        if rule_names:
            rules_destination = project_state.get_rules_destination_path(self.config, target)
            # For local: use absolute path; for remote: use path relative to remote base
            rules_dest_str = str(rules_destination)

            for rule_name in rule_names:
                install_info = self._install_command_with_backend(rule_name, rules_dest_str, backend, use_copy, target)
                installed_rules_list.append(install_info)

        # Install commands if requested
        if install_commands and command_names:
            commands_destination = project_state.get_commands_destination_path(self.config, target)
            # For local: use absolute path; for remote: use path relative to remote base
            commands_dest_str = str(commands_destination)

            for command_name in command_names:
                install_info = self._install_command_with_backend(command_name, commands_dest_str, backend, use_copy, target)
                installed_commands_list.append(install_info)

        # Add the target
        project_state.add_target(
            target=target,
            install_type=install_type,
            has_rules=bool(rule_names),
            has_commands=install_commands,
            installed_rules=installed_rules_list,
            installed_commands=installed_commands_list
        )

        # Update state
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def update_project(self, project_name: str, target: Optional[str] = None) -> ProjectState:
        """Update an existing project installation.

        Args:
            project_name: Name of the project
            target: Specific target to update. If None, updates all targets.
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

        # Verify project path still exists
        if not project_state.path.exists():
            raise FileNotFoundError(f"Project path no longer exists: {project_state.path}")

        # Determine which targets to update
        if target:
            if not project_state.has_target(target):
                raise WardenError(f"Project '{project_name}' does not have target '{target}' installed")
            targets_to_update = [target]
        else:
            targets_to_update = list(project_state.targets.keys())

        # Update each target
        for target_name in targets_to_update:
            target_config = project_state.targets[target_name]

            # Update rules if installed
            if target_config.get('has_rules'):
                print(f"[INFO] Updating rules for target '{target_name}'")
                print("WARNING: Built-in rules are meta-rules for MDC format definition.")
                print("   Project rules should come from packages. Consider using package rules instead.")

            # Update commands if installed
            if target_config.get('has_commands'):
                print(f"[INFO] Updating commands for target '{target_name}'")
                # Note: _update_commands needs to be adapted for multi-target, but for now we skip it
                # as it's mainly used for the old single-target approach

        # Update timestamp
        project_state.timestamp = datetime.now(timezone.utc).isoformat()
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def sever_project(self, project_name: str, target: Optional[str] = None, rule_name: Optional[str] = None,
                      skip_confirm: bool = False) -> ProjectState:
        """Convert symlinks to copies for project-specific modifications.

        Args:
            project_name: Name of the project
            target: Specific target to sever. If None, severs all targets.
            rule_name: Specific rule to sever (not yet implemented)
            skip_confirm: Skip confirmation prompt
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

        # Ask for confirmation unless skipped
        if not skip_confirm:
            targets_to_check = [target] if target else list(project_state.targets.keys())
            symlink_targets = [t for t in targets_to_check if project_state.targets[t]['install_type'] == 'symlink']

            if symlink_targets:
                print(f"\n[WARNING] About to sever project '{project_name}'")
                print(f"   This will convert symlinks to copies for: {', '.join(symlink_targets)}")
                print("   After severing, the project will NOT auto-update when central rules change")
                print("   You will need to manually update or use 'warden project update' to sync changes")
                response = input(f"\n   Sever '{project_name}'? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print(f"   Cancelled severing of '{project_name}'")
                    raise WardenError("Operation cancelled by user")

        # Verify project path still exists
        if not project_state.path.exists():
            raise FileNotFoundError(f"Project path no longer exists: {project_state.path}")

        # Determine which targets to sever
        if target:
            if not project_state.has_target(target):
                raise WardenError(f"Project '{project_name}' does not have target '{target}' installed")
            targets_to_sever = [target]
        else:
            targets_to_sever = list(project_state.targets.keys())

        # Sever each target
        for target_name in targets_to_sever:
            target_config = project_state.targets[target_name]

            # Only process if it's currently a symlink
            if target_config['install_type'] != 'symlink':
                print(f"[INFO] Target '{target_name}' is already using copies, skipping")
                continue

            # Get the rules directory for this target
            rules_dir = project_state.get_rules_destination_path(self.config, target_name)

            # Convert all rule files in the directory
            if not rules_dir.exists():
                print(f"[WARNING] Rules directory not found at: {rules_dir}, skipping target '{target_name}'")
                continue

            # Verify we can write to the destination
            if not os.access(rules_dir, os.W_OK):
                raise PermissionError(f"No write permission for rules directory: {rules_dir}")

            # Convert symlink to copy for all .md files
            if rule_name is None or rule_name == 'all':
                converted_any = False
                for rule_file in rules_dir.glob("*.md"):
                    if self._is_symlink_to_rules(rule_file):
                        self._convert_symlink_to_copy(rule_file)
                        converted_any = True

                if converted_any:
                    # Update target config
                    target_config['install_type'] = 'copy'
                    print(f"[SUCCESS] Severed target '{target_name}' from symlink to copy")
                else:
                    print(f"[INFO] No symlinks found for target '{target_name}'")
            else:
                # For specific rule names, we'd need to implement rule-specific handling
                raise NotImplementedError("Rule-specific severing is not yet implemented")

        # Update timestamp and save
        project_state.timestamp = datetime.now(timezone.utc).isoformat()
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def list_projects(self) -> List[ProjectState]:
        """List all registered projects."""
        projects = []
        for project_data in self.config.state['projects'].values():
            projects.append(ProjectState.from_dict(project_data))
        return projects

    def remove_project(self, project_name: str, skip_confirm: bool = False) -> bool:
        """Remove a project from tracking (does not delete files).

        Args:
            project_name: Name of the project to remove
            skip_confirm: Skip confirmation prompt

        Returns:
            True if removed, False if not found
        """
        if project_name not in self.config.state['projects']:
            return False

        # Ask for confirmation unless skipped
        if not skip_confirm:
            project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
            print(f"\n[WARNING] About to remove project '{project_name}' from tracking")
            print(f"   Path: {project_state.path}")
            print(f"   Targets: {', '.join(project_state.targets.keys())}")
            print("   Note: This will NOT delete any files, only stop tracking the project")
            response = input(f"\n   Remove '{project_name}' from tracking? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print(f"   Cancelled removal of '{project_name}'")
                return False

        del self.config.state['projects'][project_name]
        self.config.save_state()
        return True

    def rename_project(self, old_name: str, new_name: str) -> ProjectState:
        """Rename a project in the tracking system."""
        if old_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{old_name}' not found")

        if new_name in self.config.state['projects']:
            raise ProjectAlreadyExistsError(f"Project '{new_name}' already exists")

        # Validate new name
        if not new_name or not new_name.strip():
            raise WardenError("New project name cannot be empty")

        # Get the project data
        project_data = self.config.state['projects'][old_name]
        project_state = ProjectState.from_dict(project_data)

        # Update the project name
        project_state.name = new_name
        project_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Remove old entry and add new one
        del self.config.state['projects'][old_name]
        self.config.state['projects'][new_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def configure_project_targets(self, project_name: str, default_targets: List[str]) -> ProjectState:
        """Configure default targets for a project.

        Args:
            project_name: Name of the project
            default_targets: List of target names to set as defaults

        Returns:
            Updated ProjectState
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

        # Validate that all default targets are installed
        invalid_targets = [t for t in default_targets if not project_state.has_target(t)]
        if invalid_targets:
            raise WardenError(
                f"Cannot set default targets that are not installed: {', '.join(invalid_targets)}\n"
                f"Installed targets: {', '.join(project_state.targets.keys())}"
            )

        # Update default targets
        project_state.default_targets = default_targets
        project_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Save state
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def add_to_project(self, project_name: str, rule_names: Optional[List[str]] = None,
                       command_names: Optional[List[str]] = None, target: Optional[str] = None) -> ProjectState:
        """Add rules and/or commands to an existing project.

        Args:
            project_name: Name of the project
            rule_names: List of rule names to add
            command_names: List of command names to add
            target: Specific target to add to. If None, uses default_targets or all targets.
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

        # Verify project path still exists
        if not project_state.path.exists():
            raise FileNotFoundError(f"Project path no longer exists: {project_state.path}")

        # Determine which targets to update
        if target:
            if not project_state.has_target(target):
                raise WardenError(f"Project '{project_name}' does not have target '{target}' installed")
            targets_to_update = [target]
        elif project_state.default_targets:
            # Use configured default targets
            targets_to_update = [t for t in project_state.default_targets if project_state.has_target(t)]
            if not targets_to_update:
                raise WardenError(f"None of the default targets are installed for project '{project_name}'")
        else:
            # Fall back to all targets
            targets_to_update = list(project_state.targets.keys())

        # Update each target
        for target_name in targets_to_update:
            target_config = project_state.targets[target_name]
            use_copy = target_config['install_type'] == 'copy'

            # Add rules if requested
            if rule_names:
                rules_destination = project_state.get_rules_destination_path(self.config, target_name)
                self._create_target_directory(rules_destination / "dummy")

                for rule_name in rule_names:
                    # Check if rule is already installed for this target
                    already_installed = any(r.get('name') == rule_name for r in target_config['installed_rules'])
                    if already_installed:
                        print(f"[INFO] Rule '{rule_name}' is already installed for target '{target_name}', skipping")
                        continue

                    install_info = self._install_command(rule_name, rules_destination, use_copy, target_name)
                    target_config['installed_rules'].append(install_info)
                    target_config['has_rules'] = True

            # Add commands if requested
            if command_names:
                if not self.config.target_supports_commands(target_name):
                    print(f"[WARNING] Target '{target_name}' does not support custom commands, skipping")
                    continue

                commands_destination = project_state.get_commands_destination_path(self.config, target_name)
                self._create_target_directory(commands_destination / "dummy")

                for command_name in command_names:
                    # Check if command is already installed for this target
                    already_installed = any(c.get('name') == command_name for c in target_config['installed_commands'])
                    if already_installed:
                        print(f"[INFO] Command '{command_name}' is already installed for target '{target_name}', skipping")
                        continue

                    install_info = self._install_command(command_name, commands_destination, use_copy, target_name)
                    target_config['installed_commands'].append(install_info)
                    target_config['has_commands'] = True

        # Update timestamp and save
        project_state.timestamp = datetime.now(timezone.utc).isoformat()
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def install_global_config(self, target: str, force: bool = False) -> bool:
        """Install global configuration for a target."""
        global_config_path = self.config.get_global_config_path(target)

        if not global_config_path:
            raise WardenError(f"Target '{target}' does not support global configuration")

        if global_config_path.exists() and not force:
            raise WardenError(f"Global config already exists: {global_config_path}. Use --force to overwrite")

        # Create directory if it doesn't exist
        global_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate appropriate global configuration
        if target == 'claude':
            self._create_claude_global_config(global_config_path)
        elif target == 'windsurf':
            self._create_windsurf_global_config(global_config_path)
        elif target == 'codex':
            self._create_codex_global_config(global_config_path)
        else:
            raise WardenError(f"Global config generation not implemented for target: {target}")

        return True

    def _create_claude_global_config(self, config_path: Path):
        """Create or update Claude Code CLI global instructions file.

        This method preserves user's custom content in CLAUDE.md and only manages
        the Agent Warden rules section using include directives.
        """
        claude_dir = config_path.parent
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create the warden-rules.md file with all rules
        warden_rules_path = claude_dir / 'warden-rules.md'
        rules_content = self._generate_warden_rules_content()

        with open(warden_rules_path, 'w') as f:
            f.write(rules_content)

        # Now update or create CLAUDE.md with the include directive
        warden_include_line = f"@{warden_rules_path}"
        warden_section_start = "# BEGIN AGENT WARDEN MANAGED SECTION"
        warden_section_end = "# END AGENT WARDEN MANAGED SECTION"

        if config_path.exists():
            # Read existing CLAUDE.md
            existing_content = config_path.read_text()

            # Check if we already have a managed section
            if warden_section_start in existing_content:
                # Replace the managed section
                import re
                pattern = f"{re.escape(warden_section_start)}.*?{re.escape(warden_section_end)}"
                managed_section = f"{warden_section_start}\n{warden_include_line}\n{warden_section_end}"
                new_content = re.sub(pattern, managed_section, existing_content, flags=re.DOTALL)
            else:
                # Append the managed section at the end
                managed_section = f"\n\n{warden_section_start}\n{warden_include_line}\n{warden_section_end}\n"
                new_content = existing_content.rstrip() + managed_section

            with open(config_path, 'w') as f:
                f.write(new_content)
        else:
            # Create new CLAUDE.md with just the include directive
            initial_content = f"""# Claude Code CLI Global Instructions

This file contains global instructions for Claude Code CLI.
You can add your own custom instructions above or below the Agent Warden section.

{warden_section_start}
{warden_include_line}
{warden_section_end}
"""
            with open(config_path, 'w') as f:
                f.write(initial_content)

    def _generate_warden_rules_content(self) -> str:
        """Generate the content for warden-rules.md file."""
        content = f"""# Agent Warden Rules

This file is automatically generated by Agent Warden.
Do not edit manually - changes will be overwritten.

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Rules source: {self.config.base_path / 'rules'}

---

"""
        # Add all available rules from the rules directory
        rules_dir = self.config.base_path / 'rules'
        if rules_dir.exists():
            for rule_file in sorted(rules_dir.glob('*.md')):
                rule_content = rule_file.read_text()
                content += f"\n## Rule: {rule_file.stem}\n\n"
                content += rule_content + "\n\n---\n"

        return content

    def _create_windsurf_global_config(self, config_path: Path):
        """Create Windsurf global rules configuration."""
        content = f"""# Global Agent Warden Rules for Windsurf

This file contains global rules that apply to all projects in Windsurf.

## Rules Source
Rules are managed by Agent Warden from: {self.config.rules_dir}

## Available Commands
Commands are available from: {self.config.commands_path}

## Usage
These rules are automatically applied to all projects. For project-specific rules,
use Agent Warden to install rules locally to your project.

---

"""

        # Append all rules from the rules directory
        if self.config.rules_dir.exists():
            for rule_file in sorted(self.config.rules_dir.glob('*.md')):
                # Skip example directory
                if 'example' in rule_file.parts:
                    continue
                content += f"\n## Rule: {rule_file.stem}\n\n"
                content += rule_file.read_text() + "\n\n---\n"

        with open(config_path, 'w') as f:
            f.write(content)

    def _create_codex_global_config(self, config_path: Path):
        """Create Codex global configuration."""
        config_content = f"""[warden]
rules_dir = "{self.config.rules_dir}"
commands_path = "{self.config.commands_path}"

[warden.targets]
default = "augment"

[warden.behavior]
auto_update = true
use_symlinks = true

[logging]
level = "info"
file = "~/.codex/warden.log"
"""

        with open(config_path, 'w') as f:
            f.write(config_content)

    def list_available_commands(self) -> List[str]:
        """List all available commands."""
        return self._get_available_commands()

    def get_command_info(self, command_name: str) -> Dict:
        """Get information about a specific command."""
        command_path = self.config.commands_path / f"{command_name}.md"

        if not command_path.exists():
            raise FileNotFoundError(f"Command not found: {command_name}")

        content = command_path.read_text()

        # Parse frontmatter
        if content.startswith('---\n'):
            try:
                end_idx = content.find('\n---\n', 4)
                if end_idx != -1:
                    # Simple YAML parsing for frontmatter (avoiding external dependency)
                    frontmatter_text = content[4:end_idx]
                    body = content[end_idx + 5:]

                    # Parse basic YAML frontmatter manually
                    frontmatter = {}
                    for line in frontmatter_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()

                            # Handle lists (basic parsing)
                            if value.startswith('[') and value.endswith(']'):
                                # Parse simple list: ["item1", "item2"]
                                items = value[1:-1].split(',')
                                frontmatter[key] = [item.strip().strip('"\'') for item in items if item.strip()]
                            else:
                                # Remove quotes if present
                                frontmatter[key] = value.strip('"\'')

                    return {
                        'name': command_name,
                        'path': str(command_path),
                        'description': frontmatter.get('description', ''),
                        'argument_hint': frontmatter.get('argument-hint', ''),
                        'tags': frontmatter.get('tags', []),
                        'content': body.strip()
                    }
            except Exception:
                pass

        # Fallback if no frontmatter
        return {
            'name': command_name,
            'path': str(command_path),
            'description': 'No description available',
            'argument_hint': '',
            'tags': [],
            'content': content
        }

    def install_package(self, package_spec: str, ref: Optional[str] = None) -> GitHubPackage:
        """Install a GitHub package."""
        try:
            package = GitHubPackage.from_spec(package_spec)
            if ref:
                package.ref = ref
        except ValueError as e:
            raise WardenError(str(e)) from e

        package_dir = self.config.packages_path / package.directory_name

        # Check if package already exists
        if package.name in self.config.registry['packages']:
            GitHubPackage.from_dict(self.config.registry['packages'][package.name])
            if package_dir.exists():
                raise WardenError(f"Package '{package.name}' is already installed")

        print(f"[INSTALL] Installing package {package.name}@{package.ref}...")

        # Clone the repository as a submodule
        code, stdout, stderr = self._run_git_command([
            'submodule', 'add', '-b', package.ref,
            package.github_url, str(package_dir)
        ], cwd=self.config.base_path)

        if code != 0:
            # Try regular clone if submodule fails
            code, stdout, stderr = self._run_git_command([
                'clone', '-b', package.ref, package.github_url, str(package_dir)
            ], cwd=self.config.base_path)

            if code != 0:
                raise WardenError(f"Failed to clone repository: {stderr}")

        # Get the actual commit hash
        code, commit_hash, stderr = self._run_git_command(['rev-parse', 'HEAD'], cwd=package_dir)
        if code == 0:
            package.installed_ref = commit_hash

        # Discover package content
        content = self._discover_package_content(package_dir)

        # Update registry
        package_data = package.to_dict()
        package_data['content'] = content
        self.config.registry['packages'][package.name] = package_data
        self.config.save_registry()

        print(f"[SUCCESS] Package {package.name} installed successfully")
        if content['rules']:
            print(f"   Rules: {', '.join(content['rules'])}")
        if content['commands']:
            print(f"   Commands: {', '.join(content['commands'])}")

        return package

    def update_package(self, package_name: str, ref: Optional[str] = None) -> GitHubPackage:
        """Update a GitHub package."""
        if package_name not in self.config.registry['packages']:
            raise WardenError(f"Package '{package_name}' not found")

        package_data = self.config.registry['packages'][package_name]
        package = GitHubPackage.from_dict(package_data)

        if ref:
            package.ref = ref

        package_dir = self.config.packages_path / package.directory_name

        if not package_dir.exists():
            raise WardenError(f"Package directory not found: {package_dir}")

        print(f"[UPDATE] Updating package {package.name} to {package.ref}...")

        # Fetch latest changes
        code, stdout, stderr = self._run_git_command(['fetch', 'origin'], cwd=package_dir)
        if code != 0:
            raise WardenError(f"Failed to fetch updates: {stderr}")

        # Checkout the target ref
        code, stdout, stderr = self._run_git_command(['checkout', package.ref], cwd=package_dir)
        if code != 0:
            raise WardenError(f"Failed to checkout {package.ref}: {stderr}")

        # Pull if it's a branch
        if package.ref in ['main', 'master'] or not package.ref.startswith('v'):
            code, stdout, stderr = self._run_git_command(['pull', 'origin', package.ref], cwd=package_dir)

        # Get the new commit hash
        code, commit_hash, stderr = self._run_git_command(['rev-parse', 'HEAD'], cwd=package_dir)
        if code == 0:
            old_ref = package.installed_ref
            package.installed_ref = commit_hash

            if old_ref == commit_hash:
                print(f"[INFO] Package {package.name} is already up to date")
                return package

        # Rediscover content
        content = self._discover_package_content(package_dir)

        # Update registry
        package_data = package.to_dict()
        package_data['content'] = content
        self.config.registry['packages'][package.name] = package_data
        self.config.save_registry()

        print(f"[SUCCESS] Package {package.name} updated successfully")
        return package

    def remove_package(self, package_name: str) -> bool:
        """Remove a GitHub package."""
        if package_name not in self.config.registry['packages']:
            return False

        package_data = self.config.registry['packages'][package_name]
        package = GitHubPackage.from_dict(package_data)
        package_dir = self.config.packages_path / package.directory_name

        # Remove the directory
        if package_dir.exists():
            shutil.rmtree(package_dir)

        # Remove from registry
        del self.config.registry['packages'][package_name]
        self.config.save_registry()

        print(f"[SUCCESS] Package {package.name} removed successfully")
        return True

    def list_packages(self) -> List[GitHubPackage]:
        """List all installed packages."""
        packages = []
        for package_data in self.config.registry['packages'].values():
            packages.append(GitHubPackage.from_dict(package_data))
        return packages

    def check_package_updates(self) -> Dict[str, Dict]:
        """Check for updates to installed packages."""
        updates = {}

        for package_name, package_data in self.config.registry['packages'].items():
            package = GitHubPackage.from_dict(package_data)
            package_dir = self.config.packages_path / package.directory_name

            if not package_dir.exists():
                continue

            # Fetch latest changes
            code, stdout, stderr = self._run_git_command(['fetch', 'origin'], cwd=package_dir)
            if code != 0:
                continue

            # Get remote commit hash
            code, remote_hash, stderr = self._run_git_command([
                'rev-parse', f'origin/{package.ref}'
            ], cwd=package_dir)

            if code == 0 and remote_hash != package.installed_ref:
                # Get commit count difference
                code, commit_count, stderr = self._run_git_command([
                    'rev-list', '--count', f'{package.installed_ref}..{remote_hash}'
                ], cwd=package_dir)

                updates[package_name] = {
                    'current': package.installed_ref[:8],
                    'latest': remote_hash[:8],
                    'commits_behind': int(commit_count) if code == 0 else 0
                }

        return updates

    def check_project_status(self, project_name: str) -> Dict:
        """Check if project has outdated rules or commands with three-way comparison.

        Checks all targets in the project.
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
        status = {
            'outdated_rules': [],
            'outdated_commands': [],
            'user_modified_rules': [],
            'user_modified_commands': [],
            'conflict_rules': [],
            'conflict_commands': [],
            'missing_sources': [],
            'missing_installed': []
        }

        # Check each target
        for target_name, target_config in project_state.targets.items():
            # Check rules for this target
            for rule_info in target_config.get('installed_rules', []):
                if not rule_info.get('source'):
                    status['missing_sources'].append({
                        'name': rule_info['name'],
                        'type': 'rule',
                        'target': target_name,
                        'source': 'unknown (legacy installation)'
                    })
                    continue

                source_path = Path(rule_info['source'])
                dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{rule_info['name']}.md"

                if not source_path.exists():
                    status['missing_sources'].append({
                        'name': rule_info['name'],
                        'type': 'rule',
                        'target': target_name,
                        'source': str(source_path)
                    })
                    continue

                # Check if installed file exists
                if not dest_path.exists():
                    status['missing_installed'].append({
                        'name': rule_info['name'],
                        'type': 'rule',
                        'target': target_name,
                        'dest': str(dest_path)
                    })
                    continue

                # Three-way comparison
                stored_checksum = rule_info['checksum']  # What we think is installed
                source_checksum = calculate_file_checksum(source_path)  # Current source
                installed_checksum = calculate_file_checksum(dest_path)  # What's actually installed

                source_changed = source_checksum != stored_checksum
                user_modified = installed_checksum != stored_checksum

                if source_changed and user_modified:
                    # Both changed - conflict
                    status['conflict_rules'].append({
                        'name': rule_info['name'],
                        'target': target_name,
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'stored_checksum': stored_checksum,
                        'source_checksum': source_checksum,
                        'installed_checksum': installed_checksum
                    })
                elif source_changed:
                    # Only source changed - update available
                    status['outdated_rules'].append({
                        'name': rule_info['name'],
                        'target': target_name,
                        'source': str(source_path),
                        'stored_checksum': stored_checksum,
                        'source_checksum': source_checksum
                    })
                elif user_modified:
                    # Only user modified - local changes
                    status['user_modified_rules'].append({
                        'name': rule_info['name'],
                        'target': target_name,
                        'dest': str(dest_path),
                        'stored_checksum': stored_checksum,
                        'installed_checksum': installed_checksum
                    })

            # Check commands for this target
            for cmd_info in target_config.get('installed_commands', []):
                if not cmd_info.get('source'):
                    status['missing_sources'].append({
                        'name': cmd_info['name'],
                        'type': 'command',
                        'target': target_name,
                        'source': 'unknown (legacy installation)'
                    })
                    continue

                source_path = Path(cmd_info['source'])
                dest_path = project_state.get_commands_destination_path(self.config, target_name) / f"{cmd_info['name']}.md"

                if not source_path.exists():
                    status['missing_sources'].append({
                        'name': cmd_info['name'],
                        'type': 'command',
                        'target': target_name,
                        'source': str(source_path)
                    })
                    continue

                # Check if installed file exists
                if not dest_path.exists():
                    status['missing_installed'].append({
                        'name': cmd_info['name'],
                        'type': 'command',
                        'target': target_name,
                        'dest': str(dest_path)
                    })
                    continue

                # Three-way comparison
                stored_checksum = cmd_info['checksum']
                source_checksum = calculate_file_checksum(source_path)
                installed_checksum = calculate_file_checksum(dest_path)

                source_changed = source_checksum != stored_checksum
                user_modified = installed_checksum != stored_checksum

                if source_changed and user_modified:
                    # Both changed - conflict
                    status['conflict_commands'].append({
                        'name': cmd_info['name'],
                        'target': target_name,
                        'source': str(source_path),
                        'dest': str(dest_path),
                        'stored_checksum': stored_checksum,
                        'source_checksum': source_checksum,
                        'installed_checksum': installed_checksum
                    })
                elif source_changed:
                    # Only source changed - update available
                    status['outdated_commands'].append({
                        'name': cmd_info['name'],
                        'target': target_name,
                        'source': str(source_path),
                        'stored_checksum': stored_checksum,
                        'source_checksum': source_checksum
                    })
                elif user_modified:
                    # Only user modified - local changes
                    status['user_modified_commands'].append({
                        'name': cmd_info['name'],
                        'target': target_name,
                        'dest': str(dest_path),
                        'stored_checksum': stored_checksum,
                        'installed_checksum': installed_checksum
                    })

        return status

    def check_all_projects_status(self, include_remote: Optional[bool] = None) -> Dict[str, Dict]:
        """Check status of all projects.

        Args:
            include_remote: If True, include remote projects. If False, skip remote projects.
                          If None, use config setting (default: True)
        """
        # Determine whether to include remote projects
        if include_remote is None:
            include_remote = self.config.config.get('update_remote_projects', True)

        all_status = {}
        for project_name in self.config.state['projects']:
            # Check if this is a remote project and should be skipped
            project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
            if not include_remote and project_state.is_remote():
                continue

            try:
                status = self.check_project_status(project_name)
                if (status['outdated_rules'] or status['outdated_commands'] or
                    status['missing_sources'] or status['conflict_rules'] or status['conflict_commands']):
                    all_status[project_name] = status
            except Exception as e:
                all_status[project_name] = {'error': str(e)}
        return all_status

    def show_diff(self, project_name: str, item_name: str, target: Optional[str] = None) -> str:
        """Show diff between installed and current version of a rule or command.

        Args:
            project_name: Name of the project
            item_name: Name of the rule or command
            target: Specific target to show diff for. If None, shows first found.
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

        # Find the item in rules or commands across all targets
        item_info = None
        dest_path = None

        # Search through targets
        targets_to_search = [target] if target else list(project_state.targets.keys())

        for target_name in targets_to_search:
            target_config = project_state.targets.get(target_name)
            if not target_config:
                continue

            # Search in rules
            for rule in target_config.get('installed_rules', []):
                if rule['name'] == item_name:
                    item_info = rule
                    dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{item_name}.md"
                    break

            if item_info:
                break

            # Search in commands
            for cmd in target_config.get('installed_commands', []):
                if cmd['name'] == item_name:
                    item_info = cmd
                    dest_path = project_state.get_commands_destination_path(self.config, target_name) / f"{item_name}.md"
                    break

            if item_info:
                break

        if not item_info:
            raise WardenError(f"Item '{item_name}' not found in project '{project_name}'")

        source_path = Path(item_info['source'])
        if not source_path.exists():
            raise WardenError(f"Source file not found: {source_path}")

        if not dest_path.exists():
            raise WardenError(f"Installed file not found: {dest_path}")

        # Read both files
        with open(dest_path) as f:
            installed_lines = f.readlines()

        with open(source_path) as f:
            current_lines = f.readlines()

        # Generate unified diff
        diff = difflib.unified_diff(
            installed_lines,
            current_lines,
            fromfile=f"installed/{item_name}",
            tofile=f"current/{item_name}",
            lineterm=''
        )

        return '\n'.join(diff)

    def update_project_items(self, project_name: str, rule_names: Optional[List[str]] = None,
                            command_names: Optional[List[str]] = None, update_all: bool = False,
                            force: bool = False, skip_confirm: bool = False, target: Optional[str] = None) -> Dict:
        """Update specific rules/commands or all outdated items in a project.

        Args:
            project_name: Name of the project to update
            rule_names: Specific rules to update (None = none)
            command_names: Specific commands to update (None = none)
            update_all: Update all outdated items
            force: Force update even for conflicts without prompting
            skip_confirm: Skip confirmation prompts (auto-answer yes)
            target: Specific target to update (None = all targets)
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
        updated = {'rules': [], 'commands': [], 'errors': [], 'skipped': []}

        # Get project status to identify conflicts
        status = self.check_project_status(project_name)

        # Determine what to update
        items_to_update = {'rules': [], 'commands': []}
        conflicts = {'rules': [], 'commands': []}

        if update_all:
            # Get all outdated items
            items_to_update['rules'] = [r['name'] for r in status['outdated_rules']]
            items_to_update['commands'] = [c['name'] for c in status['outdated_commands']]
            # Also include conflicts
            conflicts['rules'] = [r['name'] for r in status['conflict_rules']]
            conflicts['commands'] = [c['name'] for c in status['conflict_commands']]
        else:
            # Check if specified items are in conflict
            for rule_name in (rule_names or []):
                if any(r['name'] == rule_name for r in status['conflict_rules']):
                    conflicts['rules'].append(rule_name)
                else:
                    items_to_update['rules'].append(rule_name)

            for cmd_name in (command_names or []):
                if any(c['name'] == cmd_name for c in status['conflict_commands']):
                    conflicts['commands'].append(cmd_name)
                else:
                    items_to_update['commands'].append(cmd_name)

        # Handle conflicts for rules
        for rule_name in conflicts['rules']:
            if not force and not skip_confirm:
                # Ask for confirmation
                print(f"\n[CONFLICT] Rule '{rule_name}' has both source updates AND local modifications.")
                print("   Updating will OVERWRITE your local changes.")
                response = input(f"   Update '{rule_name}' anyway? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    updated['skipped'].append(rule_name)
                    print(f"   Skipped '{rule_name}'")
                    continue
            elif not force and skip_confirm:
                # Skip confirmation but don't force - skip conflicts
                updated['skipped'].append(rule_name)
                print(f"   Skipped '{rule_name}' (conflict, use --force to override)")
                continue

            # Add to items to update
            items_to_update['rules'].append(rule_name)

        # Handle conflicts for commands
        for cmd_name in conflicts['commands']:
            if not force and not skip_confirm:
                # Ask for confirmation
                print(f"\n[CONFLICT] Command '{cmd_name}' has both source updates AND local modifications.")
                print("   Updating will OVERWRITE your local changes.")
                response = input(f"   Update '{cmd_name}' anyway? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    updated['skipped'].append(cmd_name)
                    print(f"   Skipped '{cmd_name}'")
                    continue
            elif not force and skip_confirm:
                # Skip confirmation but don't force - skip conflicts
                updated['skipped'].append(cmd_name)
                print(f"   Skipped '{cmd_name}' (conflict, use --force to override)")
                continue

            # Add to items to update
            items_to_update['commands'].append(cmd_name)

        # Determine which targets to update
        targets_to_update = [target] if target else list(project_state.targets.keys())

        # Update rules across specified targets
        for rule_name in items_to_update['rules']:
            try:
                # Find the rule info across specified targets
                found = False
                for target_name, target_config in project_state.targets.items():
                    # Skip if not in targets to update
                    if target_name not in targets_to_update:
                        continue

                    rule_info = None
                    rule_index = None
                    for i, r in enumerate(target_config.get('installed_rules', [])):
                        if r['name'] == rule_name:
                            rule_info = r
                            rule_index = i
                            found = True
                            break

                    if not rule_info:
                        continue

                    # Get source and destination paths
                    source_path = Path(rule_info['source'])
                    dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{rule_name}.md"

                    if not source_path.exists():
                        updated['errors'].append(f"Source file not found for '{rule_name}' in target '{target_name}': {source_path}")
                        continue

                    # Copy the updated file
                    shutil.copy2(source_path, dest_path)

                    # Update checksum
                    new_checksum = calculate_file_checksum(source_path)
                    target_config['installed_rules'][rule_index]['checksum'] = new_checksum
                    target_config['installed_rules'][rule_index]['installed_at'] = datetime.now(timezone.utc).isoformat()

                if found and rule_name not in updated['rules']:
                    updated['rules'].append(rule_name)
                elif not found:
                    updated['errors'].append(f"Rule '{rule_name}' not found in any target")

            except Exception as e:
                updated['errors'].append(f"Error updating rule '{rule_name}': {e}")

        # Update commands across specified targets
        for cmd_name in items_to_update['commands']:
            try:
                # Find the command info across specified targets
                found = False
                for target_name, target_config in project_state.targets.items():
                    # Skip if not in targets to update
                    if target_name not in targets_to_update:
                        continue

                    cmd_info = None
                    cmd_index = None
                    for i, c in enumerate(target_config.get('installed_commands', [])):
                        if c['name'] == cmd_name:
                            cmd_info = c
                            cmd_index = i
                            found = True
                            break

                    if not cmd_info:
                        continue

                    # Get source and destination paths
                    source_path = Path(cmd_info['source'])
                    dest_path = project_state.get_commands_destination_path(self.config, target_name) / f"{cmd_name}.md"

                    if not source_path.exists():
                        updated['errors'].append(f"Source file not found for '{cmd_name}' in target '{target_name}': {source_path}")
                        continue

                    # Copy the updated file
                    shutil.copy2(source_path, dest_path)

                    # Update checksum
                    new_checksum = calculate_file_checksum(source_path)
                    target_config['installed_commands'][cmd_index]['checksum'] = new_checksum
                    target_config['installed_commands'][cmd_index]['installed_at'] = datetime.now(timezone.utc).isoformat()

                if found and cmd_name not in updated['commands']:
                    updated['commands'].append(cmd_name)
                elif not found:
                    updated['errors'].append(f"Command '{cmd_name}' not found in any target")

            except Exception as e:
                updated['errors'].append(f"Error updating command '{cmd_name}': {e}")

        # Save updated state
        if updated['rules'] or updated['commands']:
            self.config.state['projects'][project_name] = project_state.to_dict()
            self.config.save_state()

        return updated

    def install_to_all_projects(self, rule_names: Optional[List[str]] = None,
                                command_names: Optional[List[str]] = None,
                                target: Optional[str] = None,
                                skip_confirm: bool = False) -> Dict:
        """Install rules and/or commands to all registered projects.

        Args:
            rule_names: List of rule names to install
            command_names: List of command names to install
            target: Specific target to install to (if None, uses project defaults)
            skip_confirm: Skip confirmation prompt

        Returns:
            Dict with summary of installed, skipped, and error projects
        """
        if not rule_names and not command_names:
            raise WardenError("Must specify at least one rule or command to install")

        summary = {
            'installed': [],  # List of (project_name, installed_items) tuples
            'skipped': [],  # List of project names that were skipped
            'errors': []  # List of (project_name, error) tuples
        }

        projects = self.list_projects()
        if not projects:
            raise WardenError("No projects registered. Use 'warden install <path>' to register a project first.")

        # Show what will be installed
        print(f"[INFO] Installing to {len(projects)} project(s):")
        for project in projects:
            print(f"  • {project.name}")
        if rule_names:
            print(f"[INFO] Rules: {', '.join(rule_names)}")
        if command_names:
            print(f"[INFO] Commands: {', '.join(command_names)}")
        if target:
            print(f"[INFO] Target: {target}")
        print()

        # Confirm unless skip_confirm is True
        if not skip_confirm:
            response = input("Continue? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                raise WardenError("Installation cancelled by user")

        # Install to each project
        for project in projects:
            try:
                self.add_to_project(
                    project.name,
                    rule_names=rule_names,
                    command_names=command_names,
                    target=target
                )

                installed_items = {
                    'rules': rule_names or [],
                    'commands': command_names or []
                }
                summary['installed'].append((project.name, installed_items))

            except Exception as e:
                summary['errors'].append((project.name, str(e)))

        return summary

    def update_all_projects(self, dry_run: bool = False, include_remote: Optional[bool] = None) -> Dict:
        """Update all projects with outdated items, skipping conflicts.

        Args:
            dry_run: If True, only show what would be updated without making changes
            include_remote: If True, include remote projects. If False, skip remote projects.
                          If None, use config setting (default: True)

        Returns:
            Dict with summary of updated, skipped, and error projects
        """
        # Determine whether to include remote projects
        if include_remote is None:
            include_remote = self.config.config.get('update_remote_projects', True)

        summary = {
            'updated': [],  # List of (project_name, updated_items) tuples
            'skipped_conflicts': [],  # List of (project_name, conflicts) tuples
            'skipped_uptodate': [],  # List of project names that are up to date
            'skipped_remote': [],  # List of remote project names that were skipped
            'errors': []  # List of (project_name, error) tuples
        }

        # Check all projects - this returns only projects with issues
        all_status = self.check_all_projects_status()

        # Track which projects have issues
        projects_with_issues = set(all_status.keys())

        # All other projects are up to date or skipped
        for project_name in self.config.state['projects']:
            if project_name not in projects_with_issues:
                # Check if this is a remote project and should be skipped
                project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
                if not include_remote and project_state.is_remote():
                    summary['skipped_remote'].append(project_name)
                else:
                    summary['skipped_uptodate'].append(project_name)

        # Process each project with issues
        for project_name, status in all_status.items():
            # Check if this is a remote project and should be skipped
            project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
            if not include_remote and project_state.is_remote():
                summary['skipped_remote'].append(project_name)
                continue

            if 'error' in status:
                summary['errors'].append((project_name, status['error']))
                continue

            # Check if project has conflicts
            has_conflicts = status.get('conflict_rules') or status.get('conflict_commands')

            if has_conflicts:
                conflicts = {
                    'rules': [r['name'] for r in status.get('conflict_rules', [])],
                    'commands': [c['name'] for c in status.get('conflict_commands', [])]
                }
                summary['skipped_conflicts'].append((project_name, conflicts))
                continue

            # Check if project has outdated items
            has_outdated = status.get('outdated_rules') or status.get('outdated_commands')

            if not has_outdated:
                summary['skipped_uptodate'].append(project_name)
                continue

            # Update the project (skip conflicts automatically by not forcing)
            if not dry_run:
                try:
                    result = self.update_project_items(
                        project_name,
                        update_all=True,
                        force=False  # Don't force conflicts
                    )

                    updated_items = {
                        'rules': result['rules'],
                        'commands': result['commands'],
                        'skipped': result.get('skipped', []),
                        'errors': result.get('errors', [])
                    }
                    summary['updated'].append((project_name, updated_items))

                except Exception as e:
                    summary['errors'].append((project_name, str(e)))
            else:
                # Dry run - just record what would be updated
                would_update = {
                    'rules': [r['name'] for r in status.get('outdated_rules', [])],
                    'commands': [c['name'] for c in status.get('outdated_commands', [])],
                    'skipped': [],
                    'errors': []
                }
                summary['updated'].append((project_name, would_update))

        return summary

    def show_package_diff(self, package_name: str, show_files: bool = False) -> str:
        """Show diff for a package that has updates available."""
        if package_name not in self.config.registry['packages']:
            raise WardenError(f"Package '{package_name}' not found")

        package_data = self.config.registry['packages'][package_name]
        package = GitHubPackage.from_dict(package_data)
        package_dir = self.config.packages_path / package.directory_name

        if not package_dir.exists():
            raise WardenError(f"Package directory not found: {package_dir}")

        # Fetch latest changes
        code, stdout, stderr = self._run_git_command(['fetch', 'origin'], cwd=package_dir)
        if code != 0:
            raise WardenError(f"Failed to fetch updates: {stderr}")

        # Get remote commit hash
        code, remote_hash, stderr = self._run_git_command([
            'rev-parse', f'origin/{package.ref}'
        ], cwd=package_dir)

        if code != 0:
            raise WardenError(f"Failed to get remote commit: {stderr}")

        if remote_hash == package.installed_ref:
            return f"Package {package.name} is up to date"

        # Show commit log
        code, commit_log, stderr = self._run_git_command([
            'log', '--oneline', '--no-merges',
            f'{package.installed_ref}..{remote_hash}'
        ], cwd=package_dir)

        diff_output = f"[PACKAGE] Package: {package.name}\n"
        diff_output += f"[UPDATE] Current: {package.installed_ref[:8]}\n"
        diff_output += f"🆕 Latest:  {remote_hash[:8]}\n\n"

        if code == 0 and commit_log:
            diff_output += "[NOTE] Recent commits:\n"
            for line in commit_log.split('\n')[:10]:  # Show last 10 commits
                diff_output += f"  • {line}\n"

        if show_files:
            # Show file changes
            code, file_changes, stderr = self._run_git_command([
                'diff', '--name-status',
                f'{package.installed_ref}..{remote_hash}'
            ], cwd=package_dir)

            if code == 0 and file_changes:
                diff_output += "\n[FOLDER] Changed files:\n"
                for line in file_changes.split('\n'):
                    if line.strip():
                        status, filename = line.split('\t', 1)
                        status_icon = {'A': '[ADD]', 'M': '[NOTE]', 'D': '[ERROR]'}.get(status, '[UPDATE]')
                        diff_output += f"  {status_icon} {filename}\n"

        return diff_output

    def get_package_status(self) -> Dict[str, str]:
        """Get status of all packages (up-to-date, outdated, error)."""
        status = {}

        for package_name in self.config.registry['packages']:
            try:
                package_data = self.config.registry['packages'][package_name]
                package = GitHubPackage.from_dict(package_data)
                package_dir = self.config.packages_path / package.directory_name

                if not package_dir.exists():
                    status[package_name] = 'missing'
                    continue

                # Check if we can fetch (network connectivity)
                code, stdout, stderr = self._run_git_command(['fetch', 'origin'], cwd=package_dir)
                if code != 0:
                    status[package_name] = 'error'
                    continue

                # Check if up to date
                code, remote_hash, stderr = self._run_git_command([
                    'rev-parse', f'origin/{package.ref}'
                ], cwd=package_dir)

                if code == 0:
                    if remote_hash == package.installed_ref:
                        status[package_name] = 'up-to-date'
                    else:
                        status[package_name] = 'outdated'
                else:
                    status[package_name] = 'error'

            except Exception:
                status[package_name] = 'error'

        return status


class AutoUpdater:
    """Handles automatic updates for Agent Warden."""

    def __init__(self, config: WardenConfig):
        self.config = config
        self.repo_path = Path(__file__).parent.resolve()
        self.script_path = Path(__file__).resolve()

    def should_check_for_updates(self) -> bool:
        """Check if we should check for updates based on frequency and config."""
        # Check if auto-update is enabled
        if not self.config.config.get('auto_update', True):
            return False

        # Check last update check time
        last_check = self.config.state.get('last_update_check')
        if last_check:
            try:
                last_check_time = datetime.fromisoformat(last_check)
                time_since_check = datetime.now() - last_check_time
                # Check once per day (24 hours)
                if time_since_check.total_seconds() < 86400:
                    return False
            except (ValueError, TypeError):
                # Invalid timestamp, proceed with check
                pass

        return True

    def is_git_repository(self) -> bool:
        """Check if the current directory is a git repository."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def is_git_clean(self) -> bool:
        """Check if git working directory is clean."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and not result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def is_system_wide_install(self) -> bool:
        """Detect if running from system-wide installation vs repository."""
        # If script is in site-packages or dist-packages, it's system-wide
        script_str = str(self.script_path)
        return 'site-packages' in script_str or 'dist-packages' in script_str

    def check_for_updates(self) -> Optional[Dict]:
        """Check if updates are available. Returns update info or None."""
        if not self.is_git_repository():
            return None

        try:
            # Fetch latest changes from remote
            result = subprocess.run(
                ['git', 'fetch', 'origin', 'main'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Silently fail on network errors
                return None

            # Get local commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            local_hash = result.stdout.strip()

            # Get remote commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'origin/main'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            remote_hash = result.stdout.strip()

            # Check if we're behind
            if local_hash == remote_hash:
                return None

            # Count commits behind
            result = subprocess.run(
                ['git', 'rev-list', '--count', f'{local_hash}..{remote_hash}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            commits_behind = 0
            if result.returncode == 0:
                try:
                    commits_behind = int(result.stdout.strip())
                except ValueError:
                    commits_behind = 0

            return {
                'local_hash': local_hash,
                'remote_hash': remote_hash,
                'commits_behind': commits_behind
            }

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # Silently fail on any errors
            return None

    def perform_update(self) -> bool:
        """Perform the actual update. Returns True if successful."""
        if not self.is_git_repository():
            return False

        if not self.is_git_clean():
            print("[INFO] Skipping auto-update: git working directory has uncommitted changes")
            return False

        try:
            print("\n[UPDATE] Updating Agent Warden...")

            # Perform git pull --rebase
            result = subprocess.run(
                ['git', 'pull', '--rebase', 'origin', 'main'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"[WARNING] Update failed: {result.stderr}")
                return False

            # If system-wide install, reinstall
            if self.is_system_wide_install():
                print("[UPDATE] Reinstalling system-wide package...")
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '--upgrade', '-e', str(self.repo_path)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    print(f"[WARNING] Reinstall failed: {result.stderr}")
                    return False

            print("[SUCCESS] Agent Warden updated successfully!")
            return True

        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"[WARNING] Update failed: {e}")
            return False

    def update_last_check_time(self):
        """Update the last update check timestamp."""
        self.config.state['last_update_check'] = datetime.now(timezone.utc).isoformat()
        self.config.save_state()


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Agent Warden - Manage and synchronize agentic AI tool configurations across multiple projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install rules to ALL registered projects
  %(prog)s install --rules coding-no-emoji git-commit
  %(prog)s install --commands code-review test-gen

  # Install to specific existing project
  %(prog)s install --project my-project --rules git-commit

  # Install rules to new project (registers it)
  %(prog)s install /path/to/project --target augment --rules coding-no-emoji

  # Install to remote server via SSH
  %(prog)s install user@server.com:/var/www/app --target augment --rules coding-no-emoji
  %(prog)s install myserver:/home/dev/project --target cursor --rules git-commit

  # Install with custom name
  %(prog)s install /path/to/app --name my-project --rules coding-no-emoji

  # Install both rules and commands
  %(prog)s install --rules coding-no-emoji --commands code-review

  # Install package rules
  %(prog)s install /path/to/project --rules owner/repo:typescript

  # Project management
  %(prog)s project list
  %(prog)s project my-project          # Show project details
  %(prog)s project update              # Update ALL projects
  %(prog)s project update my_project   # Update specific project
  %(prog)s project update my_project --target cursor  # Update only cursor target
  %(prog)s project update my_project --force  # Force update conflicts
  %(prog)s project sever my_project --target augment  # Sever only augment target
  %(prog)s project rename old-name new-name
  %(prog)s project remove my_project

  # Configure default target
  %(prog)s config --set-default-target augment
  %(prog)s config --auto-update false  # Disable automatic updates
  %(prog)s config --show

  # List available commands
  %(prog)s list-commands

  # Global configuration
  %(prog)s global-install claude
  %(prog)s global-install windsurf --force

  # Package management
  %(prog)s add-package user/repo
  %(prog)s add-package user/repo@v1.0.0
  %(prog)s update-package user/repo
  %(prog)s list-packages
  %(prog)s search api

  # Skip confirmations (for automation)
  %(prog)s project remove my-project --yes
  %(prog)s project update my-project --yes
        """
    )

    # Global flags
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip all confirmation prompts and use default answers')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Install command
    install_parser = subparsers.add_parser('install', help='Install rules and/or commands to a project')
    install_parser.add_argument('project_path', nargs='?',
                               help='Local path or remote SSH location ([user@]host:path) to the project directory (or use --project for existing)')
    install_parser.add_argument('--project', metavar='NAME',
                               help='Use existing project by name instead of path')
    install_parser.add_argument('--target', choices=['cursor', 'augment', 'claude', 'windsurf', 'codex'],
                               help='Target configuration (default: augment)')
    install_parser.add_argument('--copy', action='store_true',
                               help='Copy files instead of creating symlinks')
    install_parser.add_argument('--name', metavar='NAME',
                               help='Custom name for the project (default: directory name)')
    install_parser.add_argument('--rules', nargs='*', metavar='RULE',
                               help='Install specific rules from rules/ directory or packages')
    install_parser.add_argument('--commands', nargs='*', metavar='COMMAND',
                               help='Install commands (all if no specific commands listed)')

    # Project namespace
    project_parser = subparsers.add_parser('project', help='Project management commands')
    project_subparsers = project_parser.add_subparsers(dest='project_command', help='Project commands')

    # Project list command
    project_list_parser = project_subparsers.add_parser('list', help='List all registered projects')
    project_list_parser.add_argument('--verbose', '-v', action='store_true',
                                     help='Show detailed information including installed commands')

    # Project show command
    project_show_parser = project_subparsers.add_parser('show', help='Show detailed information about a project')
    project_show_parser.add_argument('project_name', help='Name of the project to show')

    # Project update command
    project_update_parser = project_subparsers.add_parser('update', help='Update project(s) with outdated rules/commands')
    project_update_parser.add_argument('project_name', nargs='?', help='Name of the project to update (omit to update all projects)')
    project_update_parser.add_argument('--target', metavar='TARGET',
                                       choices=['cursor', 'augment', 'claude', 'windsurf', 'codex'],
                                       help='Update only a specific target (default: all targets)')
    project_update_parser.add_argument('--rules', nargs='*', metavar='RULE', help='Update specific rules')
    project_update_parser.add_argument('--commands', nargs='*', metavar='COMMAND', help='Update specific commands')
    project_update_parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    project_update_parser.add_argument('--force', action='store_true', help='Force update conflicts without prompting')

    # Project sever command
    project_sever_parser = project_subparsers.add_parser('sever', help='Convert symlinks to copies for modifications')
    project_sever_parser.add_argument('project_name', help='Name of the project to sever')
    project_sever_parser.add_argument('--target', metavar='TARGET',
                                      choices=['cursor', 'augment', 'claude', 'windsurf', 'codex'],
                                      help='Sever only a specific target (default: all targets)')

    # Project remove command
    project_remove_parser = project_subparsers.add_parser('remove', help='Remove project from tracking')
    project_remove_parser.add_argument('project_name', help='Name of the project to remove')

    # Project rename command
    project_rename_parser = project_subparsers.add_parser('rename', help='Rename a project in the tracking system')
    project_rename_parser.add_argument('old_name', help='Current name of the project')
    project_rename_parser.add_argument('new_name', help='New name for the project')

    # Project configure command
    project_configure_parser = project_subparsers.add_parser('configure', help='Configure default targets for a project')
    project_configure_parser.add_argument('project_name', help='Name of the project to configure')
    project_configure_parser.add_argument('--targets', nargs='+', required=True,
                                         choices=['cursor', 'augment', 'claude', 'windsurf', 'codex'],
                                         help='Default targets to use when adding rules/commands')

    # List commands
    list_commands_parser = subparsers.add_parser('list-commands', help='List all available commands')
    list_commands_parser.add_argument('--info', '-i', metavar='COMMAND',
                                    help='Show detailed information about a specific command')

    # Global install command
    global_parser = subparsers.add_parser('global-install', help='Install global configuration for a target')
    global_parser.add_argument('target', choices=['claude', 'windsurf', 'codex'],
                              help='Target to install global configuration for')
    global_parser.add_argument('--force', action='store_true',
                              help='Overwrite existing global configuration')

    # Config command
    config_parser = subparsers.add_parser('config', help='View or modify Agent Warden configuration')
    config_parser.add_argument('--set-default-target', metavar='TARGET',
                              choices=['cursor', 'augment', 'claude', 'windsurf', 'codex'],
                              help='Set the default target for new installations')
    config_parser.add_argument('--update-remote', metavar='BOOL',
                              choices=['true', 'false', 'yes', 'no', 'on', 'off'],
                              help='Enable/disable updating remote projects in global update commands')
    config_parser.add_argument('--auto-update', metavar='BOOL',
                              choices=['true', 'false', 'yes', 'no', 'on', 'off'],
                              help='Enable/disable automatic updates of Agent Warden')
    config_parser.add_argument('--show', action='store_true',
                              help='Show current configuration')

    # Package management commands
    add_package_parser = subparsers.add_parser('add-package', help='Add a GitHub package')
    add_package_parser.add_argument('package_spec', help='Package specification (owner/repo[@ref])')
    add_package_parser.add_argument('--ref', help='Specific branch, tag, or commit to install')

    update_package_parser = subparsers.add_parser('update-package', help='Update a GitHub package')
    update_package_parser.add_argument('package_name', help='Name of the package to update (owner/repo)')
    update_package_parser.add_argument('--ref', help='Update to specific branch, tag, or commit')

    remove_package_parser = subparsers.add_parser('remove-package', help='Remove a GitHub package')
    remove_package_parser.add_argument('package_name', help='Name of the package to remove (owner/repo)')

    list_packages_parser = subparsers.add_parser('list-packages', help='List all installed packages')
    list_packages_parser.add_argument('--status', action='store_true',
                                     help='Show update status for each package')

    check_updates_parser = subparsers.add_parser('check-updates', help='Check for package updates')
    check_updates_parser.add_argument('--diff', metavar='PACKAGE',
                                     help='Show diff for a specific package')
    check_updates_parser.add_argument('--files', action='store_true',
                                     help='Show changed files in diff')

    search_parser = subparsers.add_parser('search', help='Search for rules and commands')
    search_parser.add_argument('query', help='Search query')

    # Status command
    status_parser = subparsers.add_parser('status', help='Check for outdated rules and commands')
    status_parser.add_argument('project_name', nargs='?', help='Project name (optional, checks all if not specified)')

    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Show differences between installed and current versions')
    diff_parser.add_argument('project_name', help='Project name')
    diff_parser.add_argument('item_name', help='Rule or command name')

    return parser


def format_project_info(project: ProjectState, verbose: bool = False) -> str:
    """Format project information for display."""
    target_names = list(project.targets.keys())
    targets_str = ', '.join(target_names) if target_names else 'none'

    info = (f"📦 {project.name}\n"
            f"   Path: {project.path}\n"
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


def format_project_detailed(project: ProjectState, manager: 'WardenManager') -> str:
    """Format detailed project information with status of installed items."""
    target_names = list(project.targets.keys())
    targets_str = ', '.join(target_names) if target_names else 'none'

    info = (f"📦 {project.name}\n"
            f"   Path: {project.path}\n"
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
                for rule_info in target_config['installed_rules']:
                    rule_name = rule_info['name'] if isinstance(rule_info, dict) else rule_info
                    rule_status = get_item_status(rule_name, 'rule', status)
                    info += f"         • {rule_name} {rule_status}\n"

            # Display commands
            if target_config.get('has_commands') and target_config.get('installed_commands'):
                info += f"      Commands ({len(target_config['installed_commands'])}):\n"
                for cmd_info in target_config['installed_commands']:
                    cmd_name = cmd_info['name'] if isinstance(cmd_info, dict) else cmd_info
                    cmd_status = get_item_status(cmd_name, 'command', status)
                    info += f"         • {cmd_name} {cmd_status}\n"
    except Exception as e:
        info += f"\n   [WARNING] Could not retrieve status: {e}\n"

    return info


def get_item_status(item_name: str, item_type: str, status: Dict) -> str:
    """Get status indicator for an item."""
    # Check if item is in any status category
    if item_type == 'rule':
        if any(r['name'] == item_name for r in status.get('conflict_rules', [])):
            return "[CONFLICT]"
        if any(r['name'] == item_name for r in status.get('user_modified_rules', [])):
            return "[MODIFIED]"
        if any(r['name'] == item_name for r in status.get('outdated_rules', [])):
            return "[OUTDATED]"
        if any(r['name'] == item_name for r in status.get('missing_sources', []) if r.get('type') == 'rule'):
            return "[MISSING SOURCE]"
        if any(r['name'] == item_name for r in status.get('missing_installed', []) if r.get('type') == 'rule'):
            return "[MISSING FILE]"
    else:  # command
        if any(c['name'] == item_name for c in status.get('conflict_commands', [])):
            return "[CONFLICT]"
        if any(c['name'] == item_name for c in status.get('user_modified_commands', [])):
            return "[MODIFIED]"
        if any(c['name'] == item_name for c in status.get('outdated_commands', [])):
            return "[OUTDATED]"
        if any(c['name'] == item_name for c in status.get('missing_sources', []) if c.get('type') == 'command'):
            return "[MISSING SOURCE]"
        if any(c['name'] == item_name for c in status.get('missing_installed', []) if c.get('type') == 'command'):
            return "[MISSING FILE]"

    return "[UP TO DATE]"


def main():
    """Main entry point."""
    parser = create_parser()

    # Intercept 'project <name>' and convert to 'project show <name>'
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == 'project':
        # Check if the second argument is not a known subcommand
        known_subcommands = ['list', 'show', 'update', 'sever', 'remove', 'rename', 'configure']
        if sys.argv[2] not in known_subcommands and not sys.argv[2].startswith('-'):
            # Insert 'show' before the project name
            sys.argv.insert(2, 'show')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Track if we should perform update at exit
    update_info = None

    try:
        # Check for WARDEN_HOME environment variable for testing/development
        warden_home = os.environ.get('WARDEN_HOME')
        if warden_home:
            print(f"[INFO] Using WARDEN_HOME: {warden_home}")
            manager = WardenManager(base_path=warden_home)
        else:
            manager = WardenManager()

        # Check for updates (once per day, if enabled)
        auto_updater = AutoUpdater(manager.config)
        if auto_updater.should_check_for_updates():
            update_info = auto_updater.check_for_updates()
            auto_updater.update_last_check_time()

            if update_info:
                commits = update_info['commits_behind']
                print(f"[INFO] Agent Warden update available ({commits} commit{'s' if commits != 1 else ''} behind)")
                print("[INFO] Update will be applied after command completes")
                print()

        if args.command == 'project':
            # Handle project subcommands
            if not hasattr(args, 'project_command') or not args.project_command:
                # No subcommand provided, show help
                parser.parse_args(['project', '--help'])
                return 1

            if args.project_command == 'list':
                projects = manager.list_projects()
                if not projects:
                    print("No projects registered.")
                else:
                    print(f"Registered projects ({len(projects)}):\n")
                    for project in projects:
                        print(format_project_info(project, verbose=args.verbose))
                        print()

            elif args.project_command == 'show':
                try:
                    project_state = manager.config.state['projects'].get(args.project_name)
                    if not project_state:
                        print(f"[ERROR] Project '{args.project_name}' not found")
                        return 1

                    project = ProjectState.from_dict(project_state)
                    print(format_project_detailed(project, manager))
                except Exception as e:
                    print(f"[ERROR] {e}")
                    return 1

            elif args.project_command == 'update':
                try:
                    dry_run = args.dry_run if hasattr(args, 'dry_run') and args.dry_run else False

                    # Check if updating all projects or a specific project
                    if not args.project_name:
                        # Update all projects
                        if dry_run:
                            print("[DRY RUN] Showing what would be updated:\n")

                        summary = manager.update_all_projects(dry_run=dry_run)

                        # Display results
                        if summary['updated']:
                            action = "Would update" if dry_run else "Updated"
                            print(f"[SUCCESS] {action} {len(summary['updated'])} project(s):\n")
                            for project_name, items in summary['updated']:
                                print(f"  📦 {project_name}:")
                                if items['rules']:
                                    print(f"     Rules: {', '.join(items['rules'])}")
                                if items['commands']:
                                    print(f"     Commands: {', '.join(items['commands'])}")
                                if items.get('skipped'):
                                    print(f"     Skipped (conflicts): {', '.join(items['skipped'])}")
                                if items.get('errors'):
                                    print(f"     Errors: {len(items['errors'])}")
                                print()

                        if summary['skipped_conflicts']:
                            print(f"[CONFLICT] Skipped {len(summary['skipped_conflicts'])} project(s) with conflicts (need manual resolution):\n")
                            for project_name, conflicts in summary['skipped_conflicts']:
                                print(f"  ⚠️  {project_name}:")
                                if conflicts['rules']:
                                    print(f"     Conflicted rules: {', '.join(conflicts['rules'])}")
                                if conflicts['commands']:
                                    print(f"     Conflicted commands: {', '.join(conflicts['commands'])}")
                                print(f"     → Use: warden project update {project_name} --force")
                                print()

                        if summary['skipped_remote']:
                            print(f"[INFO] Skipped {len(summary['skipped_remote'])} remote project(s) (remote updates disabled)")
                            print("      → Enable with: warden config --update-remote true")
                            print("      → Or update individually: warden project update <project-name>")

                        if summary['skipped_uptodate']:
                            print(f"[INFO] {len(summary['skipped_uptodate'])} project(s) already up to date")

                        if summary['errors']:
                            print(f"\n[ERROR] Errors in {len(summary['errors'])} project(s):")
                            for project_name, error in summary['errors']:
                                print(f"  • {project_name}: {error}")

                        if not summary['updated'] and not summary['skipped_conflicts'] and not summary['errors']:
                            print("[INFO] All projects are up to date")

                    else:
                        # Update specific project
                        rule_names = args.rules if hasattr(args, 'rules') and args.rules is not None else None
                        command_names = args.commands if hasattr(args, 'commands') and args.commands is not None else None
                        force = args.force if hasattr(args, 'force') and args.force else False
                        target = args.target if hasattr(args, 'target') and args.target else None

                        # Determine if updating all items or specific ones
                        update_all = not rule_names and not command_names

                        if dry_run:
                            # Dry run for specific project
                            status = manager.check_project_status(args.project_name)
                            print(f"[DRY RUN] Would update project '{args.project_name}':\n")
                            if target:
                                print(f"  Target: {target}")

                            if status['outdated_rules']:
                                print(f"  Rules to update: {', '.join([r['name'] for r in status['outdated_rules']])}")
                            if status['outdated_commands']:
                                print(f"  Commands to update: {', '.join([c['name'] for c in status['outdated_commands']])}")
                            if status['conflict_rules']:
                                print(f"  Conflicted rules (would skip): {', '.join([r['name'] for r in status['conflict_rules']])}")
                            if status['conflict_commands']:
                                print(f"  Conflicted commands (would skip): {', '.join([c['name'] for c in status['conflict_commands']])}")

                            if not status['outdated_rules'] and not status['outdated_commands']:
                                print("  No updates needed")
                        else:
                            # Actually update
                            result = manager.update_project_items(
                                args.project_name,
                                rule_names=rule_names,
                                command_names=command_names,
                                update_all=update_all,
                                force=force,
                                skip_confirm=args.yes,
                                target=target
                            )

                            if result['rules'] or result['commands']:
                                print(f"[SUCCESS] Updated project '{args.project_name}':")
                                if target:
                                    print(f"   Target: {target}")
                                if result['rules']:
                                    print(f"   Rules: {', '.join(result['rules'])}")
                                if result['commands']:
                                    print(f"   Commands: {', '.join(result['commands'])}")
                            else:
                                print(f"[INFO] No items updated for project '{args.project_name}'")

                            if result.get('skipped'):
                                print(f"\n[INFO] Skipped {len(result['skipped'])} item(s) due to conflicts:")
                                for item in result['skipped']:
                                    print(f"   • {item}")
                                print("   Use --force to update conflicts")

                            if result['errors']:
                                print("\n[WARNING] Errors encountered:")
                                for error in result['errors']:
                                    print(f"   • {error}")

                except (ProjectNotFoundError, WardenError) as e:
                    print(f"[ERROR] {e}")
                    return 1

            elif args.project_command == 'sever':
                try:
                    target = args.target if hasattr(args, 'target') and args.target else None
                    project = manager.sever_project(args.project_name, target=target, skip_confirm=args.yes)
                    print(f"[SUCCESS] Successfully severed project '{project.name}'")
                    if target:
                        print(f"   Target: {target}")
                    print("   Converted from symlink to copy")
                except WardenError as e:
                    print(f"[ERROR] {e}")
                    return 1

            elif args.project_command == 'remove':
                if manager.remove_project(args.project_name, skip_confirm=args.yes):
                    print(f"[SUCCESS] Removed project '{args.project_name}' from tracking")
                else:
                    print(f"[ERROR] Project '{args.project_name}' not found")
                    return 1

            elif args.project_command == 'rename':
                try:
                    project = manager.rename_project(args.old_name, args.new_name)
                    print(f"[SUCCESS] Successfully renamed project '{args.old_name}' to '{args.new_name}'")
                    print(f"   Path: {project.path}")
                    print(f"   Target: {project.target}")
                except (ProjectNotFoundError, ProjectAlreadyExistsError, WardenError) as e:
                    print(f"[ERROR] {e}")
                    return 1

            elif args.project_command == 'configure':
                try:
                    project = manager.configure_project_targets(args.project_name, args.targets)
                    print(f"[SUCCESS] Configured default targets for project '{project.name}'")
                    print(f"   Default Targets: {', '.join(project.default_targets)}")
                    print("\n   Now you can add rules without specifying --target:")
                    print(f"   warden install --project {project.name} --rules my-rule")
                    print(f"   (will install to: {', '.join(project.default_targets)})")
                except (ProjectNotFoundError, WardenError) as e:
                    print(f"[ERROR] {e}")
                    return 1

        elif args.command == 'install':
            rule_names = args.rules if hasattr(args, 'rules') and args.rules is not None else None
            command_names = args.commands if args.commands else None
            target = args.target if hasattr(args, 'target') and args.target else None

            # Check if installing to all projects, specific project, or new project
            if args.project:
                # Add to specific existing project
                if not rule_names and not command_names:
                    print("[ERROR] Must specify --rules or --commands when using --project")
                    return 1

                project = manager.add_to_project(args.project, rule_names, command_names, target)

                print(f"[SUCCESS] Successfully added to project '{project.name}'")
                if rule_names:
                    print(f"   Added Rules: {', '.join(rule_names)}")
                if command_names:
                    print(f"   Added Commands: {', '.join(command_names)}")
                print(f"   Path: {project.path}")

            elif not args.project_path:
                # Install to all projects (no project_path and no --project specified)
                if not rule_names and not command_names:
                    print("[ERROR] Must specify --rules or --commands to install")
                    return 1

                try:
                    summary = manager.install_to_all_projects(
                        rule_names=rule_names,
                        command_names=command_names,
                        target=target,
                        skip_confirm=args.yes
                    )

                    # Display results
                    if summary['installed']:
                        print(f"\n[SUCCESS] Installed to {len(summary['installed'])} project(s):\n")
                        for project_name, items in summary['installed']:
                            print(f"  📦 {project_name}:")
                            if items['rules']:
                                print(f"     Rules: {', '.join(items['rules'])}")
                            if items['commands']:
                                print(f"     Commands: {', '.join(items['commands'])}")
                            print()

                    if summary['errors']:
                        print(f"\n[ERROR] Errors in {len(summary['errors'])} project(s):")
                        for project_name, error in summary['errors']:
                            print(f"  • {project_name}: {error}")

                    if not summary['installed'] and not summary['errors']:
                        print("[INFO] No projects to install to")

                except WardenError as e:
                    print(f"[ERROR] {e}")
                    return 1

            else:
                # New installation to specific path
                install_commands = args.commands is not None
                custom_name = args.name if hasattr(args, 'name') and args.name else None

                project = manager.install_project(
                    args.project_path,
                    args.target,
                    args.copy,
                    install_commands=install_commands,
                    command_names=command_names,
                    rule_names=rule_names,
                    custom_name=custom_name
                )

                print(f"[SUCCESS] Successfully installed for project '{project.name}'")
                targets_str = ', '.join(project.targets.keys())
                print(f"   Targets: {targets_str}")

                # Show details for each target
                for target_name, target_config in project.targets.items():
                    print(f"\n   [{target_name}]")
                    if target_config.get('has_rules') and target_config.get('installed_rules'):
                        print(f"      Rules: {project.get_rules_destination_path(manager.config, target_name)}")
                        rule_names_display = [r['name'] if isinstance(r, dict) else r for r in target_config['installed_rules']]
                        print(f"      Installed Rules: {', '.join(rule_names_display)}")
                    if target_config.get('has_commands') and target_config.get('installed_commands'):
                        print(f"      Commands: {project.get_commands_destination_path(manager.config, target_name)}")
                        cmd_names = [c['name'] if isinstance(c, dict) else c for c in target_config['installed_commands']]
                        print(f"      Installed Commands: {', '.join(cmd_names)}")
                    print(f"      Type: {target_config['install_type']}")

        elif args.command == 'list-commands':
            if args.info:
                # Show detailed info about a specific command
                try:
                    command_info = manager.get_command_info(args.info)
                    print(f"[LIST] Command: {command_info['name']}")
                    print(f"   Description: {command_info['description']}")
                    if command_info['argument_hint']:
                        print(f"   Usage: /{command_info['name']} {command_info['argument_hint']}")
                    if command_info['tags']:
                        print(f"   Tags: {', '.join(command_info['tags'])}")
                    print(f"   Path: {command_info['path']}")
                    print(f"\n📖 Content:\n{command_info['content'][:500]}...")
                except FileNotFoundError as e:
                    print(f"[ERROR] {e}")
                    return 1
            else:
                # List all available commands
                commands = manager.list_available_commands()
                if not commands:
                    print("No commands available.")
                else:
                    print(f"Available commands ({len(commands)}):\n")
                    for command in commands:
                        try:
                            info = manager.get_command_info(command)
                            print(f"[LIST] {command}")
                            print(f"   {info['description']}")
                            if info['tags']:
                                print(f"   Tags: {', '.join(info['tags'])}")
                            print()
                        except Exception:
                            print(f"[LIST] {command}")
                            print("   No description available")
                            print()

        elif args.command == 'global-install':
            try:
                manager.install_global_config(args.target, args.force)
                global_path = manager.config.get_global_config_path(args.target)
                print(f"[SUCCESS] Successfully installed global configuration for {args.target}")
                print(f"   Configuration: {global_path}")

                if args.target == 'claude':
                    warden_rules_path = global_path.parent / 'warden-rules.md'
                    print(f"   Rules file: {warden_rules_path}")
                    print(f"   Note: Your custom instructions in {global_path.name} are preserved")
            except WardenError as e:
                print(f"[ERROR] {e}")
                return 1

        elif args.command == 'add-package':
            try:
                package = manager.install_package(args.package_spec, args.ref)
                print(f"[CELEBRATE] Package '{package.name}' is ready to use!")
                print(f"   Use package commands with: {package.name}:command-name")
            except WardenError as e:
                print(f"[ERROR] {e}")
                return 1

        elif args.command == 'update-package':
            try:
                package = manager.update_package(args.package_name, args.ref)
                print(f"[CELEBRATE] Package '{package.name}' updated successfully!")
            except WardenError as e:
                print(f"[ERROR] {e}")
                return 1

        elif args.command == 'remove-package':
            if manager.remove_package(args.package_name):
                print(f"[SUCCESS] Package '{args.package_name}' removed successfully")
            else:
                print(f"[ERROR] Package '{args.package_name}' not found")
                return 1

        elif args.command == 'list-packages':
            packages = manager.list_packages()
            if not packages:
                print("No packages installed.")
                print("\n[TIP] Add packages with: warden add-package owner/repo")
            else:
                print(f"[PACKAGE] Installed packages ({len(packages)}):\n")

                if args.status:
                    status_map = manager.get_package_status()

                for package in packages:
                    status_icon = "[PACKAGE]"
                    status_text = ""

                    if args.status and package.name in status_map:
                        status = status_map[package.name]
                        if status == 'up-to-date':
                            status_icon = "[SUCCESS]"
                            status_text = " (up-to-date)"
                        elif status == 'outdated':
                            status_icon = "[UPDATE]"
                            status_text = " (update available)"
                        elif status == 'error':
                            status_icon = "[ERROR]"
                            status_text = " (error)"
                        elif status == 'missing':
                            status_icon = "❓"
                            status_text = " (missing)"

                    print(f"{status_icon} {package.name}@{package.ref}{status_text}")
                    print(f"   Installed: {package.installed_at}")

                    # Show available content
                    package_data = manager.config.registry['packages'].get(package.name, {})
                    content = package_data.get('content', {})
                    if content.get('rules'):
                        print(f"   [LIST] Rules: {', '.join(content['rules'])}")
                    if content.get('commands'):
                        print(f"   [TOOL] Commands: {', '.join(content['commands'])}")
                    print()

        elif args.command == 'check-updates':
            if args.diff:
                try:
                    diff_output = manager.show_package_diff(args.diff, args.files)
                    print(diff_output)
                except WardenError as e:
                    print(f"[ERROR] {e}")
                    return 1
            else:
                print("[SEARCH] Checking for updates...")
                updates = manager.check_package_updates()

                if not updates:
                    print("[SUCCESS] All packages are up to date!")
                else:
                    print(f"[PACKAGE] Updates available for {len(updates)} package(s):\n")
                    for package_name, update_info in updates.items():
                        commits = update_info['commits_behind']
                        print(f"[UPDATE] {package_name}")
                        print(f"   Current: {update_info['current']}")
                        print(f"   Latest:  {update_info['latest']}")
                        print(f"   Behind:  {commits} commit{'s' if commits != 1 else ''}")
                        print(f"   Update:  warden update-package {package_name}")
                        print()

                    print("[TIP] Use --diff PACKAGE to see changes before updating")

        elif args.command == 'search':
            results = manager.search_packages(args.query)

            total_results = len(results['rules']) + len(results['commands'])
            if total_results == 0:
                print(f"No results found for '{args.query}'")
            else:
                print(f"[SEARCH] Search results for '{args.query}' ({total_results} found):\n")

                if results['rules']:
                    print("[LIST] Rules:")
                    for rule in results['rules']:
                        print(f"   • {rule}")
                    print()

                if results['commands']:
                    print("[TOOL] Commands:")
                    for cmd in results['commands']:
                        print(f"   • {cmd}")
                    print()

                # Provide helpful installation tips
                tips = []
                if results['rules'] and results['commands']:
                    tips.append("Install rules: warden install /path/to/project --rules <rule-name>")
                    tips.append("Install commands: warden install /path/to/project --commands <command-name>")
                elif results['rules']:
                    tips.append("Install with: warden install /path/to/project --rules <rule-name>")
                elif results['commands']:
                    tips.append("Install with: warden install /path/to/project --commands <command-name>")

                if tips:
                    print("[TIP]")
                    for tip in tips:
                        print(f"   {tip}")

        elif args.command == 'status':
            if args.project_name:
                # Check specific project
                try:
                    status = manager.check_project_status(args.project_name)

                    # Check if everything is clean
                    has_issues = any([
                        status['outdated_rules'], status['outdated_commands'],
                        status['user_modified_rules'], status['user_modified_commands'],
                        status['conflict_rules'], status['conflict_commands'],
                        status['missing_sources'], status['missing_installed']
                    ])

                    if not has_issues:
                        print(f"[SUCCESS] Project '{args.project_name}' is up to date and unmodified")
                    else:
                        print(f"[INFO] Status for project '{args.project_name}':\n")

                        if status['outdated_rules']:
                            print(f"[UPDATE] Source updated - rules ({len(status['outdated_rules'])}):")
                            for rule in status['outdated_rules']:
                                print(f"   • {rule['name']} (source has new version)")
                            print()

                        if status['outdated_commands']:
                            print(f"[UPDATE] Source updated - commands ({len(status['outdated_commands'])}):")
                            for cmd in status['outdated_commands']:
                                print(f"   • {cmd['name']} (source has new version)")
                            print()

                        if status['user_modified_rules']:
                            print(f"[MODIFIED] User modified - rules ({len(status['user_modified_rules'])}):")
                            for rule in status['user_modified_rules']:
                                print(f"   • {rule['name']} (local changes detected)")
                            print()

                        if status['user_modified_commands']:
                            print(f"[MODIFIED] User modified - commands ({len(status['user_modified_commands'])}):")
                            for cmd in status['user_modified_commands']:
                                print(f"   • {cmd['name']} (local changes detected)")
                            print()

                        if status['conflict_rules']:
                            print(f"[CONFLICT] Both changed - rules ({len(status['conflict_rules'])}):")
                            for rule in status['conflict_rules']:
                                print(f"   • {rule['name']} (source updated AND user modified)")
                            print()

                        if status['conflict_commands']:
                            print(f"[CONFLICT] Both changed - commands ({len(status['conflict_commands'])}):")
                            for cmd in status['conflict_commands']:
                                print(f"   • {cmd['name']} (source updated AND user modified)")
                            print()

                        if status['missing_sources']:
                            print(f"[WARNING] Missing sources ({len(status['missing_sources'])}):")
                            for item in status['missing_sources']:
                                print(f"   • {item['name']} ({item['type']}): {item['source']}")
                            print()

                        if status['missing_installed']:
                            print(f"[WARNING] Missing installed files ({len(status['missing_installed'])}):")
                            for item in status['missing_installed']:
                                print(f"   • {item['name']} ({item['type']}): {item['dest']}")
                            print()

                        print("[TIP] Use 'warden diff <project> <item>' to see changes")
                        if status['outdated_rules'] or status['outdated_commands']:
                            print("[TIP] Use 'warden project update <project> --all' to update outdated items")
                        if status['user_modified_rules'] or status['user_modified_commands']:
                            print("[TIP] User modifications will be overwritten if you update")
                        if status['conflict_rules'] or status['conflict_commands']:
                            print("[WARNING] Conflicts require manual resolution - backup user changes first!")

                except ProjectNotFoundError as e:
                    print(f"[ERROR] {e}")
                    return 1
            else:
                # Check all projects
                all_status = manager.check_all_projects_status()

                # Check if remote projects are being skipped
                include_remote = manager.config.config.get('update_remote_projects', True)
                if not include_remote:
                    # Count remote projects
                    remote_count = sum(1 for p in manager.config.state['projects'].values()
                                     if ProjectState.from_dict(p).is_remote())
                    if remote_count > 0:
                        print(f"[INFO] Skipping {remote_count} remote project(s) (remote updates disabled)")
                        print("      → Enable with: warden config --update-remote true\n")

                if not all_status:
                    print("[SUCCESS] All projects are up to date")
                else:
                    print(f"[INFO] Found {len(all_status)} project(s) with updates:\n")

                    for project_name, status in all_status.items():
                        if 'error' in status:
                            print(f"[ERROR] {project_name}: {status['error']}")
                            continue

                        outdated_count = len(status.get('outdated_rules', [])) + len(status.get('outdated_commands', []))
                        missing_count = len(status.get('missing_sources', []))

                        print(f"[UPDATE] {project_name}:")
                        if outdated_count > 0:
                            print(f"   {outdated_count} outdated item(s)")
                        if missing_count > 0:
                            print(f"   {missing_count} missing source(s)")
                        print()

                    print("[TIP] Use 'warden status <project>' for details")

        elif args.command == 'diff':
            try:
                diff_output = manager.show_diff(args.project_name, args.item_name)
                if diff_output:
                    print(diff_output)
                else:
                    print(f"[INFO] No differences found for '{args.item_name}'")
            except (ProjectNotFoundError, WardenError) as e:
                print(f"[ERROR] {e}")
                return 1

        elif args.command == 'config':
            if args.set_default_target:
                # Set the default target
                manager.config.config['default_target'] = args.set_default_target
                manager.config.save_config()
                print(f"[SUCCESS] Default target set to '{args.set_default_target}'")
            elif args.update_remote:
                # Set update_remote_projects setting
                value_map = {
                    'true': True, 'yes': True, 'on': True,
                    'false': False, 'no': False, 'off': False
                }
                new_value = value_map[args.update_remote.lower()]
                manager.config.config['update_remote_projects'] = new_value
                manager.config.save_config()
                status = "enabled" if new_value else "disabled"
                print(f"[SUCCESS] Remote project updates {status}")
                if not new_value:
                    print("[INFO] Remote projects will be skipped in 'warden project update' and 'warden status' commands")
                    print("[INFO] You can still update individual remote projects with 'warden project update <project-name>'")
            elif args.auto_update:
                # Set auto_update setting
                value_map = {
                    'true': True, 'yes': True, 'on': True,
                    'false': False, 'no': False, 'off': False
                }
                new_value = value_map[args.auto_update.lower()]
                manager.config.config['auto_update'] = new_value
                manager.config.save_config()
                status = "enabled" if new_value else "disabled"
                print(f"[SUCCESS] Automatic updates {status}")
                if not new_value:
                    print("[INFO] Agent Warden will not check for or apply updates automatically")
                    print("[INFO] You can manually update using: git pull --rebase")
                else:
                    print("[INFO] Agent Warden will check for updates once per day and apply them after commands complete")
            elif args.show:
                # Show current configuration
                print("Agent Warden Configuration:")
                print(f"   Default Target: {manager.config.config['default_target']}")
                print(f"   Update Remote Projects: {manager.config.config.get('update_remote_projects', True)}")
                print(f"   Auto Update: {manager.config.config.get('auto_update', True)}")
                print(f"   Base Path: {manager.config.base_path}")
                print(f"   Rules Directory: {manager.config.rules_dir}")
                print(f"   Commands Path: {manager.config.commands_path}")
                print(f"   Packages Path: {manager.config.packages_path}")
                print("\nAvailable Targets:")
                for target, config in manager.config.config['targets'].items():
                    supports_cmds = "✓" if config.get('supports_commands', False) else "✗"
                    print(f"   {target}: {supports_cmds} commands")
            else:
                print("[ERROR] Must specify --set-default-target, --update-remote, --auto-update, or --show")
                return 1

        # Perform auto-update if available (after successful command execution)
        if update_info:
            auto_updater.perform_update()

        return 0

    except KeyboardInterrupt:
        print("\n[ERROR] Operation cancelled by user", file=sys.stderr)
        return 1
    except (ProjectNotFoundError, ProjectAlreadyExistsError, InvalidTargetError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        print(f"[ERROR] File system error: {e}", file=sys.stderr)
        return 1
    except FileOperationError as e:
        print(f"[ERROR] File operation failed: {e}", file=sys.stderr)
        return 1
    except WardenError as e:
        print(f"[ERROR] Agent Warden error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
