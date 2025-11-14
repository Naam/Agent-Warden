#!/usr/bin/env python3
"""
Agent Warden - Manage and synchronize agentic AI tool configurations across multiple projects.

This script provides comprehensive functionality to install, update, and manage
both MDC rules and custom commands across different AI development tools with
support for symlinks, copies, and system-wide configurations.
"""

import argparse
import difflib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


class WardenError(Exception):
    """Base exception for Agent Warden errors."""
    pass


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to human-readable relative or absolute time.

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Human-readable time string like "2 hours ago" or "Jan 15, 2025 at 3:45 PM"
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
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
        "installed_at": datetime.now().isoformat()
    }


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
            'global_config': 'claude_desktop_config.json'
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
    RULES_FILE = 'mdc.mdc'
    COMMANDS_DIR = 'commands'
    PACKAGES_DIR = 'packages'
    REGISTRY_FILE = '.registry.json'

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()
        self.config_path = self.base_path / self.CONFIG_FILE
        self.state_path = self.base_path / self.STATE_FILE
        self.rules_path = self.base_path / self.RULES_FILE
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
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load config file: {e}")

        # Return default configuration
        return {
            'targets': self.TARGET_CONFIGS.copy(),
            'default_target': self.DEFAULT_TARGET
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
        system = platform.system()
        home = Path.home()

        if target == 'claude':
            if system == 'Darwin':  # macOS
                return home / 'Library' / 'Application Support' / 'Claude' / config_file
            elif system == 'Windows':
                return Path(os.environ.get('APPDATA', '')) / 'Claude' / config_file
            else:  # Linux
                return home / '.config' / 'claude' / config_file
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
        self.installed_at = installed_at or datetime.now().isoformat()
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
            path: Project path
            targets: Dict mapping target names to their configurations
            timestamp: Timestamp
            default_targets: List of default target names for this project
        """
        self.name = name
        self.path = Path(path).resolve()
        self.timestamp = timestamp or datetime.now().isoformat()

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
            'path': str(self.path),
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
                            "installed_at": data.get('timestamp', datetime.now().isoformat())
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
        """Get the full destination path for the MDC rules file.

        Args:
            config: WardenConfig instance
            target: Target to get path for
        """
        target_rules_path = config.get_target_rules_path(target)
        return self.path / target_rules_path / config.RULES_FILE

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

        # Ensure rules file exists
        if not self.config.rules_path.exists():
            raise FileNotFoundError(f"MDC rules file not found: {self.config.rules_path}")

    def _validate_project_path(self, project_path: Union[str, Path]) -> Path:
        """Validate and resolve project path."""
        try:
            path = Path(project_path).resolve()
        except (OSError, ValueError) as e:
            raise WardenError(f"Invalid project path '{project_path}': {e}") from e

        if not path.exists():
            raise FileNotFoundError(f"Project path does not exist: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"Project path is not a directory: {path}")

        # Check if we have read/write permissions
        if not os.access(path, os.R_OK):
            raise PermissionError(f"No read permission for project path: {path}")

        return path

    def _get_project_name(self, project_path: Path) -> str:
        """Generate project name from path."""
        return project_path.name

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

        # Built-in rules (from rules/ directory, not mdc.mdc)
        # Exclude the specific rules/example/ directory (shipped examples)
        rules_path = self.config.base_path / 'rules'
        if rules_path.exists():
            example_dir = rules_path / 'example'
            for file_path in rules_path.rglob('*.mdc'):
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
            rules_path = self.config.base_path / 'rules' / f"{command_spec}.mdc"
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

            # Try multiple possible rules directories
            possible_rules_dirs = ['rules', 'rules-mdc', 'mdc-rules', 'cursor-rules']
            for dir_name in possible_rules_dirs:
                rule_path = package_dir / dir_name / f"{rule_name}.mdc"
                if rule_path.exists():
                    return rule_path, f"package:{package_name}"

            raise FileNotFoundError(f"Rule '{rule_name}' not found in package '{package_name}'")
        else:
            raise FileNotFoundError("No built-in rules available for installation. Use package rules instead.")

    def search_packages(self, query: str) -> Dict[str, List[str]]:
        """Search for rules and commands across all packages."""
        results = {'rules': [], 'commands': []}

        query_lower = query.lower()

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

        possible_rules_dirs = ['rules', 'rules-mdc', 'mdc-rules', 'cursor-rules']
        for dir_name in possible_rules_dirs:
            rules_dir = package_path / dir_name
            if rules_dir.exists():
                for rule_file in rules_dir.rglob('*.mdc'):
                    rel_path = rule_file.relative_to(rules_dir)
                    rule_name = str(rel_path.with_suffix(''))

                    if rule_name.lower() in ['mdc', 'meta', 'format', 'template']:
                        continue

                    content['rules'].append(rule_name)
                break

        # Look for commands in multiple possible directories
        possible_commands_dirs = ['commands', 'commands-mdc', 'mdc-commands', 'cursor-commands']
        for dir_name in possible_commands_dirs:
            commands_dir = package_path / dir_name
            if commands_dir.exists():
                for cmd_file in commands_dir.rglob('*.md'):
                    rel_path = cmd_file.relative_to(commands_dir)
                    content['commands'].append(str(rel_path.with_suffix('')))
                break  # Use first found directory

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

    def _install_command(self, command_spec: str, destination_dir: Path, use_copy: bool) -> Dict:
        """Install a specific command or rule to the destination. Returns installation info with checksum."""
        try:
            source_path, source_type = self._resolve_command_path(command_spec)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Command '{command_spec}' not found: {e}") from e

        if ':' in command_spec:
            _, command_name = command_spec.split(':', 1)
        else:
            command_name = command_spec

        if source_path.suffix == '.mdc':
            dest_filename = f"{command_name}.mdc"
        else:
            dest_filename = f"{command_name}.md"

        dest_path = destination_dir / dest_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        checksum = calculate_file_checksum(source_path)

        if use_copy:
            self._copy_file(source_path, dest_path)
        else:
            self._create_symlink(source_path, dest_path)

        return {
            "name": command_spec,
            "checksum": checksum,
            "source": str(source_path),
            "source_type": source_type,
            "installed_at": datetime.now().isoformat()
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
        """Create a symlink from source to destination."""
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
        """Copy file from source to destination."""
        try:
            # Remove existing file if it exists
            if destination.exists():
                destination.unlink()

            # Copy file
            shutil.copy2(source, destination)
            return True
        except (OSError, shutil.Error) as e:
            raise FileOperationError(f"Failed to copy file from {source} to {destination}: {e}") from e

    def _is_symlink_to_rules(self, file_path: Path) -> bool:
        """Check if file is a symlink to our rules directory or a rule file."""
        if not file_path.is_symlink():
            return False

        try:
            target = file_path.resolve()
            # Check if it points to the old mdc.mdc file or any file in the rules directory
            return (target == self.config.rules_path or
                    target.parent == self.config.base_path / "rules" or
                    str(target).startswith(str(self.config.base_path / "rules")))
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
        """
        # Validate inputs
        project_path = self._validate_project_path(project_path)

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

        # Check if project path already exists
        existing_project_name = None
        for existing_name, existing_data in self.config.state['projects'].items():
            existing = ProjectState.from_dict(existing_data)
            if existing.path == project_path:
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
                rules_destination = project_state.get_rules_destination_path(self.config, target).parent
                self._create_target_directory(rules_destination / "dummy")

                for rule_name in rule_names:
                    install_info = self._install_command(rule_name, rules_destination, use_copy)
                    installed_rules_list.append(install_info)

            # Install commands if requested
            if install_commands and command_names:
                commands_destination = project_state.get_commands_destination_path(self.config, target)
                self._create_target_directory(commands_destination / "dummy")

                for command_name in command_names:
                    install_info = self._install_command(command_name, commands_destination, use_copy)
                    installed_commands_list.append(install_info)

            project_state.add_target(
                target=target,
                install_type=install_type,
                has_rules=bool(rule_names),
                has_commands=install_commands,
                installed_rules=installed_rules_list,
                installed_commands=installed_commands_list
            )

            project_state.timestamp = datetime.now().isoformat()
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
            project_name = self._get_project_name(project_path)

        if project_name in self.config.state['projects']:
            counter = 1
            while f"{project_name}_{counter}" in self.config.state['projects']:
                counter += 1
            project_name = f"{project_name}_{counter}"

        # Create project state with new multi-target format
        install_type = 'copy' if use_copy else 'symlink'
        installed_rules_list = []
        installed_commands_list = []

        # Create empty project state
        project_state = ProjectState(name=project_name, path=str(project_path))

        # Install rules from rules/ directory or packages
        if rule_names:
            rules_destination = project_state.get_rules_destination_path(self.config, target).parent
            self._create_target_directory(rules_destination / "dummy")

            for rule_name in rule_names:
                install_info = self._install_command(rule_name, rules_destination, use_copy)
                installed_rules_list.append(install_info)

        # Install commands if requested
        if install_commands and command_names:
            commands_destination = project_state.get_commands_destination_path(self.config, target)
            self._create_target_directory(commands_destination / "dummy")

            for command_name in command_names:
                install_info = self._install_command(command_name, commands_destination, use_copy)
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
        project_state.timestamp = datetime.now().isoformat()
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def sever_project(self, project_name: str, target: Optional[str] = None, rule_name: Optional[str] = None) -> ProjectState:
        """Convert symlinks to copies for project-specific modifications.

        Args:
            project_name: Name of the project
            target: Specific target to sever. If None, severs all targets.
            rule_name: Specific rule to sever (not yet implemented)
        """
        if project_name not in self.config.state['projects']:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][project_name])

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
            rules_dir = project_state.get_rules_destination_path(self.config, target_name).parent

            # Convert all rule files in the directory
            if not rules_dir.exists():
                print(f"[WARNING] Rules directory not found at: {rules_dir}, skipping target '{target_name}'")
                continue

            # Verify we can write to the destination
            if not os.access(rules_dir, os.W_OK):
                raise PermissionError(f"No write permission for rules directory: {rules_dir}")

            # Convert symlink to copy for all .mdc files
            if rule_name is None or rule_name == 'all':
                converted_any = False
                for rule_file in rules_dir.glob("*.mdc"):
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
        project_state.timestamp = datetime.now().isoformat()
        self.config.state['projects'][project_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def list_projects(self) -> List[ProjectState]:
        """List all registered projects."""
        projects = []
        for project_data in self.config.state['projects'].values():
            projects.append(ProjectState.from_dict(project_data))
        return projects

    def remove_project(self, project_name: str) -> bool:
        """Remove a project from tracking (does not delete files)."""
        if project_name not in self.config.state['projects']:
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
        project_state.timestamp = datetime.now().isoformat()

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
        project_state.timestamp = datetime.now().isoformat()

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
                rules_destination = project_state.get_rules_destination_path(self.config, target_name).parent
                self._create_target_directory(rules_destination / "dummy")

                for rule_name in rule_names:
                    # Check if rule is already installed for this target
                    already_installed = any(r.get('name') == rule_name for r in target_config['installed_rules'])
                    if already_installed:
                        print(f"[INFO] Rule '{rule_name}' is already installed for target '{target_name}', skipping")
                        continue

                    install_info = self._install_command(rule_name, rules_destination, use_copy)
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

                    install_info = self._install_command(command_name, commands_destination, use_copy)
                    target_config['installed_commands'].append(install_info)
                    target_config['has_commands'] = True

        # Update timestamp and save
        project_state.timestamp = datetime.now().isoformat()
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
        """Create Claude Desktop MCP configuration."""
        config = {
            "mcpServers": {
                "warden-rules": {
                    "command": "python",
                    "args": [str(self.config.base_path / "warden_server.py")],
                    "env": {
                        "WARDEN_RULES_PATH": str(self.config.rules_path),
                        "WARDEN_COMMANDS_PATH": str(self.config.commands_path)
                    }
                }
            }
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def _create_windsurf_global_config(self, config_path: Path):
        """Create Windsurf global rules configuration."""
        content = f"""# Global Agent Warden Rules for Windsurf

This file contains global rules that apply to all projects in Windsurf.

## Rules Source
Rules are managed by Agent Warden from: {self.config.rules_path}

## Available Commands
Commands are available from: {self.config.commands_path}

## Usage
These rules are automatically applied to all projects. For project-specific rules,
use Agent Warden to install rules locally to your project.

---

"""

        # Append the actual MDC rules content
        if self.config.rules_path.exists():
            content += self.config.rules_path.read_text()

        with open(config_path, 'w') as f:
            f.write(content)

    def _create_codex_global_config(self, config_path: Path):
        """Create Codex global configuration."""
        config_content = f"""[warden]
rules_path = "{self.config.rules_path}"
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
                dest_path = project_state.get_rules_destination_path(self.config, target_name).parent / f"{rule_info['name']}.mdc"

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

    def check_all_projects_status(self) -> Dict[str, Dict]:
        """Check status of all projects."""
        all_status = {}
        for project_name in self.config.state['projects']:
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
                    dest_path = project_state.get_rules_destination_path(self.config, target_name).parent / f"{item_name}.mdc"
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
                            force: bool = False) -> Dict:
        """Update specific rules/commands or all outdated items in a project.

        Args:
            project_name: Name of the project to update
            rule_names: Specific rules to update (None = none)
            command_names: Specific commands to update (None = none)
            update_all: Update all outdated items
            force: Force update even for conflicts without prompting
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
            if not force:
                # Ask for confirmation
                print(f"\n[CONFLICT] Rule '{rule_name}' has both source updates AND local modifications.")
                print("   Updating will OVERWRITE your local changes.")
                response = input(f"   Update '{rule_name}' anyway? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    updated['skipped'].append(rule_name)
                    print(f"   Skipped '{rule_name}'")
                    continue

            # Add to items to update
            items_to_update['rules'].append(rule_name)

        # Handle conflicts for commands
        for cmd_name in conflicts['commands']:
            if not force:
                # Ask for confirmation
                print(f"\n[CONFLICT] Command '{cmd_name}' has both source updates AND local modifications.")
                print("   Updating will OVERWRITE your local changes.")
                response = input(f"   Update '{cmd_name}' anyway? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    updated['skipped'].append(cmd_name)
                    print(f"   Skipped '{cmd_name}'")
                    continue

            # Add to items to update
            items_to_update['commands'].append(cmd_name)

        # Update rules across all targets
        for rule_name in items_to_update['rules']:
            try:
                # Find the rule info across all targets
                found = False
                for target_name, target_config in project_state.targets.items():
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
                    dest_path = project_state.get_rules_destination_path(self.config, target_name).parent / f"{rule_name}.mdc"

                    if not source_path.exists():
                        updated['errors'].append(f"Source file not found for '{rule_name}' in target '{target_name}': {source_path}")
                        continue

                    # Copy the updated file
                    shutil.copy2(source_path, dest_path)

                    # Update checksum
                    new_checksum = calculate_file_checksum(source_path)
                    target_config['installed_rules'][rule_index]['checksum'] = new_checksum
                    target_config['installed_rules'][rule_index]['installed_at'] = datetime.now().isoformat()

                if found and rule_name not in updated['rules']:
                    updated['rules'].append(rule_name)
                elif not found:
                    updated['errors'].append(f"Rule '{rule_name}' not found in any target")

            except Exception as e:
                updated['errors'].append(f"Error updating rule '{rule_name}': {e}")

        # Update commands across all targets
        for cmd_name in items_to_update['commands']:
            try:
                # Find the command info across all targets
                found = False
                for target_name, target_config in project_state.targets.items():
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
                    target_config['installed_commands'][cmd_index]['installed_at'] = datetime.now().isoformat()

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

    def update_all_projects(self, dry_run: bool = False) -> Dict:
        """Update all projects with outdated items, skipping conflicts.

        Args:
            dry_run: If True, only show what would be updated without making changes

        Returns:
            Dict with summary of updated, skipped, and error projects
        """
        summary = {
            'updated': [],  # List of (project_name, updated_items) tuples
            'skipped_conflicts': [],  # List of (project_name, conflicts) tuples
            'skipped_uptodate': [],  # List of project names that are up to date
            'errors': []  # List of (project_name, error) tuples
        }

        # Check all projects - this returns only projects with issues
        all_status = self.check_all_projects_status()

        # Track which projects have issues
        projects_with_issues = set(all_status.keys())

        # All other projects are up to date
        for project_name in self.config.state['projects']:
            if project_name not in projects_with_issues:
                summary['skipped_uptodate'].append(project_name)

        # Process each project with issues
        for project_name, status in all_status.items():
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


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Agent Warden - Manage and synchronize agentic AI tool configurations across multiple projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install rules to new project
  %(prog)s install /path/to/project --target augment --rules coding-no-emoji

  # Install with custom name
  %(prog)s install /path/to/app --name my-project --rules coding-no-emoji

  # Add rules to existing project (no need to specify path/target again!)
  %(prog)s install --project my-project --rules git-commit

  # Add commands to existing project
  %(prog)s install --project my-project --commands code-review test-gen

  # Install both rules and commands to new project
  %(prog)s install /path/to/project --rules coding-no-emoji --commands code-review

  # Install package rules
  %(prog)s install /path/to/project --rules owner/repo:typescript

  # Project management
  %(prog)s project list
  %(prog)s project my-project          # Show project details
  %(prog)s project update my_project
  %(prog)s project update my_project --force  # Force update conflicts
  %(prog)s project rename old-name new-name
  %(prog)s project remove my_project

  # Configure default target
  %(prog)s config --set-default-target augment
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
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Install command
    install_parser = subparsers.add_parser('install', help='Install rules and/or commands to a project')
    install_parser.add_argument('project_path', nargs='?', help='Path to the project directory (or use --project for existing)')
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
    project_update_parser.add_argument('--rules', nargs='*', metavar='RULE', help='Update specific rules')
    project_update_parser.add_argument('--commands', nargs='*', metavar='COMMAND', help='Update specific commands')
    project_update_parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    project_update_parser.add_argument('--force', action='store_true', help='Force update conflicts without prompting')

    # Project sever command
    project_sever_parser = project_subparsers.add_parser('sever', help='Convert symlinks to copies for modifications')
    project_sever_parser.add_argument('project_name', help='Name of the project to sever')
    project_sever_parser.add_argument('rule_name', nargs='?', default='all',
                                      help='Specific rule to sever (default: all)')

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

    try:
        manager = WardenManager()

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

                        # Determine if updating all items or specific ones
                        update_all = not rule_names and not command_names

                        if dry_run:
                            # Dry run for specific project
                            status = manager.check_project_status(args.project_name)
                            print(f"[DRY RUN] Would update project '{args.project_name}':\n")

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
                                force=force
                            )

                            if result['rules'] or result['commands']:
                                print(f"[SUCCESS] Updated project '{args.project_name}':")
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
                project = manager.sever_project(args.project_name, args.rule_name)
                print(f"[SUCCESS] Successfully severed project '{project.name}'")
                print("   Converted from symlink to copy")

            elif args.project_command == 'remove':
                if manager.remove_project(args.project_name):
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
            # Check if using existing project or new installation
            if args.project:
                # Add to existing project
                rule_names = args.rules if hasattr(args, 'rules') and args.rules is not None else None
                command_names = args.commands if args.commands else None
                target = args.target if hasattr(args, 'target') and args.target else None

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
            else:
                # New installation
                if not args.project_path:
                    print("[ERROR] Must specify project_path or use --project for existing project")
                    return 1

                # Determine what to install
                install_commands = args.commands is not None
                command_names = args.commands if args.commands else None
                rule_names = args.rules if hasattr(args, 'rules') and args.rules is not None else None
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
                        print(f"      Rules: {project.get_rules_destination_path(manager.config, target_name).parent}")
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

                print("[TIP] Install with: warden install /path/to/project --commands package:command")

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
            elif args.show:
                # Show current configuration
                print("Agent Warden Configuration:")
                print(f"   Default Target: {manager.config.config['default_target']}")
                print(f"   Base Path: {manager.config.base_path}")
                print(f"   Rules Path: {manager.config.rules_path}")
                print(f"   Commands Path: {manager.config.commands_path}")
                print(f"   Packages Path: {manager.config.packages_path}")
                print("\nAvailable Targets:")
                for target, config in manager.config.config['targets'].items():
                    supports_cmds = "✓" if config.get('supports_commands', False) else "✗"
                    print(f"   {target}: {supports_cmds} commands")
            else:
                print("[ERROR] Must specify --set-default-target or --show")
                return 1

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
