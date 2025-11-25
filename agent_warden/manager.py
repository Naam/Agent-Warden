"""
Core manager for Agent Warden operations.

Handles project installation, updates, removal, and synchronization.
"""

import difflib
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from agent_warden.config import WardenConfig
from agent_warden.exceptions import (
    FileOperationError,
    InvalidTargetError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
)
from agent_warden.hal import convert_rule_format
from agent_warden.package import GitHubPackage
from agent_warden.project import ProjectState
from agent_warden.utils import (
    calculate_content_checksum,
    calculate_file_checksum,
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


class WardenManager:
    """Main manager class for Agent Warden operations."""

    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        if base_path is None:
            # Always use the directory where warden.py is located
            # This ensures state, config, packages, rules, and commands are all
            # in the agent-warden installation directory
            # Since this file is in agent_warden/, go up one level to get the repo root
            base_path = Path(__file__).parent.parent.resolve()

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
        # Resolve the path first to handle relative paths like "."
        path = Path(project_path)
        if isinstance(backend, LocalBackend):
            path = path.resolve()
        return path.name

    def _find_project_case_insensitive(self, project_name: str) -> Optional[str]:
        """Find a project by name using case-insensitive matching.

        Args:
            project_name: The project name to search for

        Returns:
            The actual project name as stored in state, or None if not found
        """
        # First try exact match (fast path)
        if project_name in self.config.state['projects']:
            return project_name

        # Try case-insensitive match
        project_name_lower = project_name.lower()
        for stored_name in self.config.state['projects'].keys():
            if stored_name.lower() == project_name_lower:
                return stored_name

        return None

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

        # Determine if this is a command file (vs a rule file)
        is_command = '/commands/' in str(destination_dir) or str(destination_dir).endswith('/commands')

        # Determine file extension based on target and file type
        # Commands always use .md, rules use target-specific extension
        if is_command:
            file_extension = '.md'
        else:
            # For rules, use target-specific extension (e.g., .mdc for cursor, .md for others)
            file_extension = self.config.get_target_rule_extension(target) if target else '.md'

        dest_filename = f"{command_name}{file_extension}"

        dest_path = destination_dir / dest_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Process template if copying a command file with a target specified
        if use_copy and is_command and target:
            content = source_path.read_text()
            rules_dir = self.config.get_target_rules_path(target)
            processed_content = process_command_template(content, target, rules_dir)
            dest_path.write_text(processed_content)
            # Store checksum of processed content, not template
            checksum = calculate_content_checksum(processed_content)
        elif use_copy:
            self._copy_file(source_path, dest_path)
            checksum = calculate_file_checksum(source_path)
        else:
            self._create_symlink(source_path, dest_path)
            checksum = calculate_file_checksum(source_path)

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

        # Determine if this is a command file (vs a rule file)
        is_command = '/commands/' in destination_dir or destination_dir.endswith('/commands')

        # Determine file extension based on target and file type
        # Commands always use .md, rules use target-specific extension
        if is_command:
            file_extension = '.md'
        else:
            # For rules, use target-specific extension (e.g., .mdc for cursor, .md for others)
            file_extension = self.config.get_target_rule_extension(target) if target else '.md'

        dest_filename = f"{command_name}{file_extension}"

        # Construct destination path
        dest_path = f"{destination_dir.rstrip('/')}/{dest_filename}"

        # Ensure parent directory exists
        backend.mkdir(destination_dir, parents=True, exist_ok=True)

        # Calculate checksum - use processed content checksum if template processing will occur
        should_process = (
            target is not None and
            source_path.suffix == '.md' and
            (isinstance(backend, RemoteBackend) or use_copy)
        )

        if should_process and is_command:
            # For commands that will be template-processed, calculate checksum from processed content
            content = source_path.read_text()
            rules_dir = self.config.get_target_rules_path(target)
            processed_content = process_command_template(content, target, rules_dir)
            checksum = calculate_content_checksum(processed_content)
        else:
            # For non-processed files or rules, use source file checksum
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

    def _batch_install_items(self, item_names: List[str], destination_dir: str,
                            backend: FileSystemBackend, use_copy: bool, target: str,
                            is_command: bool) -> List[Dict]:
        """Install multiple items in batch for better performance.

        Args:
            item_names: List of item names to install
            destination_dir: Destination directory path
            backend: Backend to use for installation
            use_copy: Whether to use copy mode
            target: Target assistant
            is_command: True if installing commands, False if installing rules

        Returns:
            List of installation info dicts with checksums
        """
        if not item_names:
            return []

        # Ensure destination directory exists
        backend.mkdir(destination_dir, parents=True, exist_ok=True)

        # Prepare all items: resolve paths, process content, calculate checksums
        items_to_install = []
        install_infos = []

        for item_spec in item_names:
            try:
                source_path, source_type = self._resolve_command_path(item_spec)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Item '{item_spec}' not found: {e}") from e

            if ':' in item_spec:
                _, item_name = item_spec.split(':', 1)
            else:
                item_name = item_spec

            # Determine file extension
            if is_command:
                file_extension = '.md'
            else:
                file_extension = self.config.get_target_rule_extension(target) if target else '.md'

            dest_filename = f"{item_name}{file_extension}"
            dest_path = f"{destination_dir.rstrip('/')}/{dest_filename}"

            # Check if we need to process the file content
            should_process = (
                target is not None and
                source_path.suffix == '.md' and
                (isinstance(backend, RemoteBackend) or use_copy)
            )

            if should_process:
                # Read and process content
                content = source_path.read_text()

                if is_command:
                    # For commands: process template variables
                    rules_dir = self.config.get_target_rules_path(target)
                    processed_content = process_command_template(content, target, rules_dir)
                else:
                    # For rules: convert format for target
                    processed_content = convert_rule_format(content, target)

                # Write to temp file for batch transfer
                import tempfile
                tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=file_extension)
                tmp.write(processed_content)
                tmp.close()

                items_to_install.append((tmp.name, dest_path, tmp.name))  # (source, dest, temp_to_cleanup)

                # Calculate checksum from processed content
                checksum = calculate_content_checksum(processed_content)
            else:
                # No processing needed
                items_to_install.append((str(source_path), dest_path, None))
                checksum = calculate_file_checksum(source_path)

            # Store installation info
            install_infos.append({
                "name": item_spec,
                "checksum": checksum,
                "source": str(source_path),
                "source_type": source_type,
                "installed_at": datetime.now(timezone.utc).isoformat()
            })

        # Batch transfer all files
        try:
            if use_copy or isinstance(backend, RemoteBackend):
                # Use batch copy for better performance
                file_pairs = [(src, dest) for src, dest, _ in items_to_install]
                backend.copy_files_batch(file_pairs)
            else:
                # Symlink mode (local only)
                for src, dest, _ in items_to_install:
                    backend.create_symlink(src, dest)
        finally:
            # Clean up temp files
            for _, _, temp_file in items_to_install:
                if temp_file:
                    Path(temp_file).unlink()

        return install_infos

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

        # If rule_names is None, install all available rules by default
        if rule_names is None:
            rule_names = self._get_available_rules()

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

                # Batch install rules for better performance
                installed_rules_list = self._batch_install_items(
                    rule_names, rules_dest_str, backend, use_copy, target, is_command=False
                )

            # Install commands if requested
            if install_commands and command_names:
                commands_destination = project_state.get_commands_destination_path(self.config, target)
                # For local: use absolute path; for remote: use path relative to remote base
                commands_dest_str = str(commands_destination)

                # Batch install commands for better performance
                installed_commands_list = self._batch_install_items(
                    command_names, commands_dest_str, backend, use_copy, target, is_command=True
                )

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

            # Batch install rules for better performance
            installed_rules_list = self._batch_install_items(
                rule_names, rules_dest_str, backend, use_copy, target, is_command=False
            )

        # Install commands if requested
        if install_commands and command_names:
            commands_destination = project_state.get_commands_destination_path(self.config, target)
            # For local: use absolute path; for remote: use path relative to remote base
            commands_dest_str = str(commands_destination)

            # Batch install commands for better performance
            installed_commands_list = self._batch_install_items(
                command_names, commands_dest_str, backend, use_copy, target, is_command=True
            )

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
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

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
        self.config.state['projects'][actual_name] = project_state.to_dict()
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
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

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

            # Convert symlink to copy for all rule files (.md and .mdc)
            if rule_name is None or rule_name == 'all':
                converted_any = False
                # Check both .md and .mdc extensions
                for pattern in ["*.md", "*.mdc"]:
                    for rule_file in rules_dir.glob(pattern):
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
        self.config.state['projects'][actual_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def list_projects(self) -> List[ProjectState]:
        """List all registered projects."""
        projects = []
        for project_data in self.config.state['projects'].values():
            projects.append(ProjectState.from_dict(project_data))
        return projects

    def untrack_project(self, project_name: str, skip_confirm: bool = False) -> bool:
        """Remove a project from tracking (does not delete files).

        Args:
            project_name: Name of the project to untrack
            skip_confirm: Skip confirmation prompt

        Returns:
            True if untracked, False if not found
        """
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            return False

        # Ask for confirmation unless skipped
        if not skip_confirm:
            project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])
            print(f"\n[WARNING] About to untrack project '{actual_name}'")
            print(f"   Path: {project_state.path}")
            print(f"   Targets: {', '.join(project_state.targets.keys())}")
            print("   Note: This will NOT delete any files, only stop tracking the project")
            response = input(f"\n   Untrack '{actual_name}'? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print(f"   Cancelled untracking of '{actual_name}'")
                return False

        del self.config.state['projects'][actual_name]
        self.config.save_state()
        return True

    def remove_from_project(self, project_name: str, rule_names: Optional[List[str]] = None,
                           command_names: Optional[List[str]] = None, target: Optional[str] = None,
                           skip_confirm: bool = False) -> Dict:
        """Remove specific rules and/or commands from a project.

        Args:
            project_name: Name of the project
            rule_names: List of rule names to remove
            command_names: List of command names to remove
            target: Specific target to remove from. If None, removes from all targets.
            skip_confirm: Skip confirmation prompt

        Returns:
            Dict with removed_rules and removed_commands lists

        Raises:
            ProjectNotFoundError: If project doesn't exist
            WardenError: If no rules or commands specified, or other errors
        """
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        if not rule_names and not command_names:
            raise WardenError("Must specify at least one rule or command to remove")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

        # Determine which targets to remove from
        if target:
            if not project_state.has_target(target):
                raise WardenError(f"Project '{project_name}' does not have target '{target}'")
            targets_to_process = [target]
        else:
            targets_to_process = list(project_state.targets.keys())

        # Ask for confirmation unless skipped
        if not skip_confirm:
            print(f"\n[WARNING] About to remove from project '{project_name}'")
            if rule_names:
                print(f"   Rules: {', '.join(rule_names)}")
            if command_names:
                print(f"   Commands: {', '.join(command_names)}")
            print(f"   Targets: {', '.join(targets_to_process)}")
            print("   Note: This will DELETE the files from the project")
            response = input("\n   Remove these items? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("   Cancelled removal")
                raise WardenError("Operation cancelled by user")

        # Get backend for file operations
        _, _, backend = self._validate_project_location(project_state.location_string)

        removed_rules = []
        removed_commands = []

        # Process each target
        for target_name in targets_to_process:
            target_config = project_state.targets[target_name]

            # Remove rules
            if rule_names:
                rules_destination = project_state.get_rules_destination_path(self.config, target_name)
                for rule_name in rule_names:
                    # Check if rule is installed
                    rule_index = None
                    for idx, r in enumerate(target_config['installed_rules']):
                        if r.get('name') == rule_name:
                            rule_index = idx
                            break

                    if rule_index is not None:
                        # Delete the file with target-specific extension
                        rule_extension = self.config.get_target_rule_extension(target_name)
                        rule_file = rules_destination / f"{rule_name}{rule_extension}"
                        try:
                            backend.remove_file(str(rule_file))
                            # Remove from state
                            target_config['installed_rules'].pop(rule_index)
                            if rule_name not in removed_rules:
                                removed_rules.append(rule_name)
                        except Exception as e:
                            print(f"[WARNING] Failed to remove rule '{rule_name}' from target '{target_name}': {e}")

                # Update has_rules flag
                target_config['has_rules'] = bool(target_config['installed_rules'])

            # Remove commands
            if command_names:
                commands_destination = project_state.get_commands_destination_path(self.config, target_name)
                for command_name in command_names:
                    # Check if command is installed
                    command_index = None
                    for idx, c in enumerate(target_config['installed_commands']):
                        if c.get('name') == command_name:
                            command_index = idx
                            break

                    if command_index is not None:
                        # Delete the file
                        command_file = commands_destination / f"{command_name}.md"
                        try:
                            backend.remove_file(str(command_file))
                            # Remove from state
                            target_config['installed_commands'].pop(command_index)
                            if command_name not in removed_commands:
                                removed_commands.append(command_name)
                        except Exception as e:
                            print(f"[WARNING] Failed to remove command '{command_name}' from target '{target_name}': {e}")

                # Update has_commands flag
                target_config['has_commands'] = bool(target_config['installed_commands'])

        # Update timestamp
        project_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Save state
        self.config.state['projects'][actual_name] = project_state.to_dict()
        self.config.save_state()

        return {
            'removed_rules': removed_rules,
            'removed_commands': removed_commands
        }

    def rename_project(self, old_name: str, new_name: str) -> ProjectState:
        """Rename a project in the tracking system.

        Args:
            old_name: Current project name
            new_name: New project name
        """
        # Find old project with case-insensitive matching
        actual_old_name = self._find_project_case_insensitive(old_name)
        if not actual_old_name:
            raise ProjectNotFoundError(f"Project '{old_name}' not found")

        # Check new name with exact match (case-sensitive to avoid conflicts)
        if new_name in self.config.state['projects']:
            raise ProjectAlreadyExistsError(f"Project '{new_name}' already exists")

        # Validate new name
        if not new_name or not new_name.strip():
            raise WardenError("New project name cannot be empty")

        # Get the project data
        project_data = self.config.state['projects'][actual_old_name]
        project_state = ProjectState.from_dict(project_data)

        # Update the project name
        project_state.name = new_name
        project_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Remove old entry and add new one
        del self.config.state['projects'][actual_old_name]
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
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

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
        self.config.state['projects'][actual_name] = project_state.to_dict()
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
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

        # Verify project path still exists (only for local projects)
        if not project_state.is_remote() and not project_state.path.exists():
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

                # Use backend-aware installation for remote projects
                if project_state.is_remote():
                    rules_dest_str = str(rules_destination)
                    project_state.backend.mkdir(rules_dest_str, parents=True, exist_ok=True)
                else:
                    self._create_target_directory(rules_destination / "dummy")

                for rule_name in rule_names:
                    # Check if rule is already installed for this target
                    already_installed = any(r.get('name') == rule_name for r in target_config['installed_rules'])
                    if already_installed:
                        print(f"[INFO] Rule '{rule_name}' is already installed for target '{target_name}', skipping")
                        continue

                    # Use appropriate installation method based on project type
                    if project_state.is_remote():
                        rules_dest_str = str(rules_destination)
                        install_info = self._install_command_with_backend(rule_name, rules_dest_str, project_state.backend, use_copy, target_name)
                    else:
                        install_info = self._install_command(rule_name, rules_destination, use_copy, target_name)

                    target_config['installed_rules'].append(install_info)
                    target_config['has_rules'] = True

            # Add commands if requested
            if command_names:
                if not self.config.target_supports_commands(target_name):
                    print(f"[WARNING] Target '{target_name}' does not support custom commands, skipping")
                    continue

                commands_destination = project_state.get_commands_destination_path(self.config, target_name)

                # Use backend-aware installation for remote projects
                if project_state.is_remote():
                    commands_dest_str = str(commands_destination)
                    project_state.backend.mkdir(commands_dest_str, parents=True, exist_ok=True)
                else:
                    self._create_target_directory(commands_destination / "dummy")

                for command_name in command_names:
                    # Check if command is already installed for this target
                    already_installed = any(c.get('name') == command_name for c in target_config['installed_commands'])
                    if already_installed:
                        print(f"[INFO] Command '{command_name}' is already installed for target '{target_name}', skipping")
                        continue

                    # Use appropriate installation method based on project type
                    if project_state.is_remote():
                        commands_dest_str = str(commands_destination)
                        install_info = self._install_command_with_backend(command_name, commands_dest_str, project_state.backend, use_copy, target_name)
                    else:
                        install_info = self._install_command(command_name, commands_destination, use_copy, target_name)

                    target_config['installed_commands'].append(install_info)
                    target_config['has_commands'] = True

        # Update timestamp and save
        project_state.timestamp = datetime.now(timezone.utc).isoformat()
        self.config.state['projects'][actual_name] = project_state.to_dict()
        self.config.save_state()

        return project_state

    def install_global_config(self, target: str, force: bool = False,
                             rule_names: Optional[List[str]] = None,
                             command_names: Optional[List[str]] = None) -> bool:
        """Install global configuration for a target.

        Args:
            target: Target to install for (cursor, claude, windsurf, codex)
            force: Overwrite existing configuration
            rule_names: List of specific rules to install (None = all rules)
            command_names: List of specific commands to install (None = all commands)
        """
        global_config_path = self.config.get_global_config_path(target)

        if not global_config_path:
            raise WardenError(f"Target '{target}' does not support global configuration")

        if global_config_path.exists() and not force:
            raise WardenError(f"Global config already exists: {global_config_path}. Use --force to overwrite")

        # Create directory if it doesn't exist
        global_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Collect installed rules info for tracking
        installed_rules_list = []

        # Determine which rules were actually installed
        if rule_names is None:
            # All rules
            if self.config.rules_dir.exists():
                for rule_file in sorted(self.config.rules_dir.glob('*.md')):
                    if 'example' in rule_file.parts:
                        continue
                    installed_rules_list.append({
                        'name': rule_file.stem,
                        'source': 'built-in',
                        'type': 'rule'
                    })
        else:
            # Specific rules
            for rule_name in rule_names:
                installed_rules_list.append({
                    'name': rule_name,
                    'source': 'built-in',
                    'type': 'rule'
                })

        # Generate appropriate global configuration
        if target == 'cursor':
            self._create_cursor_global_config(global_config_path, rule_names, command_names)
        elif target == 'claude':
            self._create_claude_global_config(global_config_path, rule_names, command_names)
        elif target == 'windsurf':
            self._create_windsurf_global_config(global_config_path, rule_names, command_names)
        elif target == 'codex':
            self._create_codex_global_config(global_config_path, rule_names, command_names)
        else:
            raise WardenError(f"Global config generation not implemented for target: {target}")

        # Create or update @global project in state
        self._update_global_project_state(target, installed_rules_list, [])

        return True

    def _update_global_project_state(self, target: str, installed_rules: List[Dict],
                                     installed_commands: List[Dict]):
        """Update or create the @global project entry in state.

        Args:
            target: Target name (cursor, claude, windsurf, codex)
            installed_rules: List of installed rule info dicts
            installed_commands: List of installed command info dicts
        """
        GLOBAL_PROJECT_NAME = '@global'

        # Get or create @global project
        if GLOBAL_PROJECT_NAME in self.config.state['projects']:
            # Load existing @global project
            project_state = ProjectState.from_dict(self.config.state['projects'][GLOBAL_PROJECT_NAME])
        else:
            # Create new @global project
            project_state = ProjectState(
                name=GLOBAL_PROJECT_NAME,
                path='@global',  # Special marker path
                targets={},
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        # Add or update the target
        project_state.add_target(
            target=target,
            install_type='copy',  # Global installs are always copies
            has_rules=bool(installed_rules),
            has_commands=bool(installed_commands),
            installed_rules=installed_rules,
            installed_commands=installed_commands
        )

        # Update timestamp
        project_state.timestamp = datetime.now(timezone.utc).isoformat()

        # Save to state
        self.config.state['projects'][GLOBAL_PROJECT_NAME] = project_state.to_dict()
        self.config.save_state()

    def _create_claude_global_config(self, config_path: Path,
                                    rule_names: Optional[List[str]] = None,
                                    command_names: Optional[List[str]] = None):
        """Create or update Claude Code CLI global instructions file.

        This method preserves user's custom content in CLAUDE.md and only manages
        the Agent Warden rules section using include directives.

        Args:
            config_path: Path to CLAUDE.md file
            rule_names: List of specific rules to install (None = all rules)
            command_names: Not used for claude global config
        """
        claude_dir = config_path.parent
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create the warden-rules.md file with all rules
        warden_rules_path = claude_dir / 'warden-rules.md'
        rules_content = self._generate_warden_rules_content(rule_names)

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

    def _generate_warden_rules_content(self, rule_names: Optional[List[str]] = None) -> str:
        """Generate the content for warden-rules.md file.

        Args:
            rule_names: List of specific rules to include (None = all rules)
        """
        content = f"""# Agent Warden Rules

This file is automatically generated by Agent Warden.
Do not edit manually - changes will be overwritten.

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Rules source: {self.config.base_path / 'rules'}

---

"""
        # Add rules from the rules directory
        rules_dir = self.config.base_path / 'rules'
        if rules_dir.exists():
            if rule_names is None:
                # Add all rules
                for rule_file in sorted(rules_dir.glob('*.md')):
                    # Skip example directory
                    if 'example' in rule_file.parts:
                        continue
                    rule_content = rule_file.read_text()
                    content += f"\n## Rule: {rule_file.stem}\n\n"
                    content += rule_content + "\n\n---\n"
            else:
                # Add specific rules
                for rule_name in rule_names:
                    rule_file = rules_dir / f"{rule_name}.md"
                    if not rule_file.exists():
                        raise WardenError(f"Rule '{rule_name}' not found in {rules_dir}")
                    rule_content = rule_file.read_text()
                    content += f"\n## Rule: {rule_file.stem}\n\n"
                    content += rule_content + "\n\n---\n"

        return content

    def _create_windsurf_global_config(self, config_path: Path,
                                      rule_names: Optional[List[str]] = None,
                                      command_names: Optional[List[str]] = None):
        """Create Windsurf global rules configuration.

        Args:
            config_path: Path to global_rules.md file
            rule_names: List of specific rules to install (None = all rules)
            command_names: Not used for windsurf
        """
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

        # Append rules from the rules directory
        if self.config.rules_dir.exists():
            if rule_names is None:
                # Add all rules
                for rule_file in sorted(self.config.rules_dir.glob('*.md')):
                    # Skip example directory
                    if 'example' in rule_file.parts:
                        continue
                    content += f"\n## Rule: {rule_file.stem}\n\n"
                    content += rule_file.read_text() + "\n\n---\n"
            else:
                # Add specific rules
                for rule_name in rule_names:
                    rule_file = self.config.rules_dir / f"{rule_name}.md"
                    if not rule_file.exists():
                        raise WardenError(f"Rule '{rule_name}' not found in {self.config.rules_dir}")
                    content += f"\n## Rule: {rule_file.stem}\n\n"
                    content += rule_file.read_text() + "\n\n---\n"

        with open(config_path, 'w') as f:
            f.write(content)

    def _create_codex_global_config(self, config_path: Path,
                                   rule_names: Optional[List[str]] = None,
                                   command_names: Optional[List[str]] = None):
        """Create Codex global configuration.

        Args:
            config_path: Path to config.toml file
            rule_names: Not used for codex (uses rules_dir reference)
            command_names: Not used for codex (uses commands_path reference)
        """
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

    def _create_cursor_global_config(self, config_path: Path,
                                    rule_names: Optional[List[str]] = None,
                                    command_names: Optional[List[str]] = None):
        """Create Cursor global rules configuration.

        Cursor looks at ~/.cursor/rules directory for global rules.
        This method creates individual rule files in that directory.

        Args:
            config_path: Path to ~/.cursor/rules directory
            rule_names: List of specific rules to install (None = all rules)
            command_names: Not used for cursor (no global commands support)
        """
        # config_path is ~/.cursor/rules (a directory, not a file)
        rules_dir = config_path
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Get list of rules to install
        if rule_names is None:
            # Install all rules
            rules_to_install = []
            if self.config.rules_dir.exists():
                for rule_file in sorted(self.config.rules_dir.glob('*.md')):
                    # Skip example directory
                    if 'example' in rule_file.parts:
                        continue
                    rules_to_install.append(rule_file)
        else:
            # Install specific rules
            rules_to_install = []
            for rule_name in rule_names:
                rule_file = self.config.rules_dir / f"{rule_name}.md"
                if not rule_file.exists():
                    raise WardenError(f"Rule '{rule_name}' not found in {self.config.rules_dir}")
                rules_to_install.append(rule_file)

        # Copy rule files to cursor global rules directory with .mdc extension
        for rule_file in rules_to_install:
            # Change extension from .md to .mdc for Cursor
            dest_filename = rule_file.stem + '.mdc'
            dest_file = rules_dir / dest_filename
            dest_file.write_text(rule_file.read_text())

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

        Args:
            project_name: Name of the project
        """
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])
        backend = project_state.backend  # Get backend for file operations

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
                # Use target-specific extension for rules
                rule_extension = self.config.get_target_rule_extension(target_name)
                dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{rule_info['name']}{rule_extension}"

                if not source_path.exists():
                    status['missing_sources'].append({
                        'name': rule_info['name'],
                        'type': 'rule',
                        'target': target_name,
                        'source': str(source_path)
                    })
                    continue

                # Check if installed file exists (backend-aware)
                if not backend.exists(str(dest_path)):
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
                installed_checksum = backend.checksum(str(dest_path))  # What's actually installed (backend-aware)

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

                # Check if installed file exists (backend-aware)
                if not backend.exists(str(dest_path)):
                    status['missing_installed'].append({
                        'name': cmd_info['name'],
                        'type': 'command',
                        'target': target_name,
                        'dest': str(dest_path)
                    })
                    continue

                # Three-way comparison
                stored_checksum = cmd_info['checksum']

                # For commands in copy mode, calculate checksum from processed template
                # to match what was actually installed
                use_copy = target_config.get('install_type') == 'copy'
                if use_copy:
                    content = source_path.read_text()
                    rules_dir = self.config.get_target_rules_path(target_name)
                    processed_content = process_command_template(content, target_name, rules_dir)
                    source_checksum = calculate_content_checksum(processed_content)
                else:
                    source_checksum = calculate_file_checksum(source_path)

                installed_checksum = backend.checksum(str(dest_path))  # Backend-aware

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
        """Check status of all projects in parallel.

        Args:
            include_remote: If True, include remote projects. If False, skip remote projects.
                          If None, use config setting (default: True)
        """
        # Determine whether to include remote projects
        if include_remote is None:
            include_remote = self.config.config.get('update_remote_projects', True)

        # Filter projects to check
        projects_to_check = []
        for project_name in self.config.state['projects']:
            # Check if this is a remote project and should be skipped
            project_state = ProjectState.from_dict(self.config.state['projects'][project_name])
            if not include_remote and project_state.is_remote():
                continue
            projects_to_check.append(project_name)

        # Check projects in parallel
        all_status = {}

        def check_single_project(project_name: str) -> Tuple[str, Dict]:
            """Check a single project and return (project_name, status)."""
            try:
                status = self.check_project_status(project_name)
                if (status['outdated_rules'] or status['outdated_commands'] or
                    status['missing_sources'] or status['missing_installed'] or
                    status['conflict_rules'] or status['conflict_commands']):
                    return (project_name, status)
                return (project_name, None)
            except Exception as e:
                return (project_name, {'error': str(e)})

        # Use ThreadPoolExecutor for parallel checking
        # Limit to 10 threads to avoid overwhelming the system
        max_workers = min(10, len(projects_to_check)) if projects_to_check else 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_project = {
                executor.submit(check_single_project, project_name): project_name
                for project_name in projects_to_check
            }

            # Collect results as they complete
            for future in as_completed(future_to_project):
                project_name, status = future.result()
                if status is not None:
                    all_status[project_name] = status

        return all_status

    def show_diff(self, project_name: str, item_name: str, target: Optional[str] = None) -> str:
        """Show diff between installed and current version of a rule or command.

        Args:
            project_name: Name of the project
            item_name: Name of the rule or command
            target: Specific target to show diff for. If None, shows first found.
        """
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])

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
                    # Use target-specific extension for rules
                    rule_extension = self.config.get_target_rule_extension(target_name)
                    dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{item_name}{rule_extension}"
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

        # Read installed file
        with open(dest_path) as f:
            installed_lines = f.readlines()

        # Read source file - process template if it's a command in copy mode
        target_config = project_state.targets.get(target_name)
        use_copy = target_config.get('install_type') == 'copy'
        is_command = item_info in target_config.get('installed_commands', [])

        if use_copy and is_command:
            # Process template to match what was installed
            content = source_path.read_text()
            rules_dir = self.config.get_target_rules_path(target_name)
            processed_content = process_command_template(content, target_name, rules_dir)
            current_lines = processed_content.splitlines(keepends=True)
        else:
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
        # Find project with case-insensitive matching
        actual_name = self._find_project_case_insensitive(project_name)
        if not actual_name:
            raise ProjectNotFoundError(f"Project '{project_name}' not found")

        project_state = ProjectState.from_dict(self.config.state['projects'][actual_name])
        backend = project_state.backend  # Get backend for file operations
        updated = {'rules': [], 'commands': [], 'errors': [], 'skipped': []}

        # Get project status to identify conflicts
        status = self.check_project_status(actual_name)

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
                    # Use target-specific extension for rules
                    rule_extension = self.config.get_target_rule_extension(target_name)
                    dest_path = project_state.get_rules_destination_path(self.config, target_name) / f"{rule_name}{rule_extension}"

                    if not source_path.exists():
                        updated['errors'].append(f"Source file not found for '{rule_name}' in target '{target_name}': {source_path}")
                        continue

                    # Copy the updated file (backend-aware)
                    backend.copy_file(str(source_path), str(dest_path))

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

                    # Check if we need to process template (for commands in copy mode)
                    use_copy = target_config.get('install_type') == 'copy'
                    if use_copy:
                        # Process template and write to temp file, then copy
                        content = source_path.read_text()
                        rules_dir = self.config.get_target_rules_path(target_name)
                        processed_content = process_command_template(content, target_name, rules_dir)

                        # Write to temp file then copy (backend-aware)
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
                            tmp.write(processed_content)
                            tmp_path = tmp.name
                        try:
                            backend.copy_file(tmp_path, str(dest_path))
                        finally:
                            Path(tmp_path).unlink()

                        # Calculate checksum from processed content
                        new_checksum = calculate_content_checksum(processed_content)
                    else:
                        # For symlinks, just copy the file (backend-aware)
                        backend.copy_file(str(source_path), str(dest_path))
                        new_checksum = calculate_file_checksum(source_path)

                    # Update checksum
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
            self.config.state['projects'][actual_name] = project_state.to_dict()
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


