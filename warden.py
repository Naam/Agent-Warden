#!/usr/bin/env python3
"""
Agent Warden - Manage and synchronize agentic AI tool configurations across multiple projects.

This script provides comprehensive functionality to install, update, and manage
both MDC rules and custom commands across different AI development tools with
support for symlinks, copies, and system-wide configurations.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# Import from agent_warden package
from agent_warden.config import WardenConfig
from agent_warden.exceptions import (
    FileOperationError,
    InvalidTargetError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
)
from agent_warden.formatting import (
    colored_status,
    format_project_detailed,
    format_project_info,
)
from agent_warden.manager import WardenManager
from agent_warden.project import ProjectState


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

            # Check if we're up to date
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

            # Only return update info if we're actually behind (not ahead)
            if commits_behind == 0:
                return None

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
  %(prog)s project configure my_project --targets cursor augment  # Set default targets
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


def main():
    """Main entry point."""
    parser = create_parser()

    # Intercept 'project <name>' and convert to 'project show <name>'
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == 'project':
        # Check if the second argument is not a known subcommand
        known_subcommands = ['list', 'show', 'update', 'sever', 'remove', 'rename', 'configure']
        if sys.argv[2] not in known_subcommands and not sys.argv[2].startswith('-'):
            # Only insert 'show' if there's no known subcommand following
            # (e.g., 'project myproject' -> 'project show myproject')
            # but NOT 'project myproject configure' -> should stay as is (error will be caught by parser)
            if len(sys.argv) < 4 or sys.argv[3] not in known_subcommands:
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
                            print(colored_status('SUCCESS', f"{action} {len(summary['updated'])} project(s):\n"))
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
                                skipped_count = len(result['skipped'])
                                print(f"\n{colored_status('INFO', f'Skipped {skipped_count} item(s) due to conflicts:')}")
                                for item in result['skipped']:
                                    print(f"   • {item}")
                                print("   Use --force to update conflicts")

                            if result['errors']:
                                print(f"\n{colored_status('WARNING', 'Errors encountered:')}")
                                for error in result['errors']:
                                    print(f"   • {error}")

                except (ProjectNotFoundError, WardenError) as e:
                    print(colored_status('ERROR', str(e)))
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
                        installed_count = len(summary['installed'])
                        print(f"\n{colored_status('SUCCESS', f'Installed to {installed_count} project(s):')}\n")
                        for project_name, items in summary['installed']:
                            print(f"  📦 {project_name}:")
                            if items['rules']:
                                print(f"     Rules: {', '.join(items['rules'])}")
                            if items['commands']:
                                print(f"     Commands: {', '.join(items['commands'])}")
                            print()

                    if summary['errors']:
                        error_count = len(summary['errors'])
                        print(f"\n{colored_status('ERROR', f'Errors in {error_count} project(s):')}")
                        for project_name, error in summary['errors']:
                            print(f"  • {project_name}: {error}")

                    if not summary['installed'] and not summary['errors']:
                        print(colored_status('INFO', 'No projects to install to'))

                except WardenError as e:
                    print(colored_status('ERROR', str(e)))
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

                print(colored_status('SUCCESS', f"Successfully installed for project '{project.name}'"))
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
                print(colored_status('SUCCESS', f"Successfully installed global configuration for {args.target}"))
                print(f"   Configuration: {global_path}")

                if args.target == 'claude':
                    warden_rules_path = global_path.parent / 'warden-rules.md'
                    print(f"   Rules file: {warden_rules_path}")
                    print(f"   Note: Your custom instructions in {global_path.name} are preserved")
            except WardenError as e:
                print(colored_status('ERROR', str(e)))
                return 1

        elif args.command == 'add-package':
            try:
                package = manager.install_package(args.package_spec, args.ref)
                print(colored_status('CELEBRATE', f"Package '{package.name}' is ready to use!"))
                print(f"   Use package commands with: {package.name}:command-name")
            except WardenError as e:
                print(colored_status('ERROR', str(e)))
                return 1

        elif args.command == 'update-package':
            try:
                package = manager.update_package(args.package_name, args.ref)
                print(colored_status('CELEBRATE', f"Package '{package.name}' updated successfully!"))
            except WardenError as e:
                print(colored_status('ERROR', str(e)))
                return 1

        elif args.command == 'remove-package':
            if manager.remove_package(args.package_name):
                print(colored_status('SUCCESS', f"Package '{args.package_name}' removed successfully"))
            else:
                print(colored_status('ERROR', f"Package '{args.package_name}' not found"))
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
                    status_icon = colored_status('PACKAGE')
                    status_text = ""

                    if args.status and package.name in status_map:
                        status = status_map[package.name]
                        if status == 'up-to-date':
                            status_icon = colored_status('SUCCESS')
                            status_text = " (up-to-date)"
                        elif status == 'outdated':
                            status_icon = colored_status('UPDATE')
                            status_text = " (update available)"
                        elif status == 'error':
                            status_icon = colored_status('ERROR')
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
                        print(colored_status('SUCCESS', f"Project '{args.project_name}' is up to date and unmodified"))
                    else:
                        print(colored_status('INFO', f"Status for project '{args.project_name}':\n"))

                        if status['outdated_rules']:
                            print(colored_status('UPDATE', f"Source updated - rules ({len(status['outdated_rules'])}):"))
                            for rule in status['outdated_rules']:
                                print(f"   • {rule['name']} (source has new version)")
                            print()

                        if status['outdated_commands']:
                            print(colored_status('UPDATE', f"Source updated - commands ({len(status['outdated_commands'])}):"))
                            for cmd in status['outdated_commands']:
                                print(f"   • {cmd['name']} (source has new version)")
                            print()

                        if status['user_modified_rules']:
                            print(colored_status('MODIFIED', f"User modified - rules ({len(status['user_modified_rules'])}):"))
                            for rule in status['user_modified_rules']:
                                print(f"   • {rule['name']} (local changes detected)")
                            print()

                        if status['user_modified_commands']:
                            print(colored_status('MODIFIED', f"User modified - commands ({len(status['user_modified_commands'])}):"))
                            for cmd in status['user_modified_commands']:
                                print(f"   • {cmd['name']} (local changes detected)")
                            print()

                        if status['conflict_rules']:
                            print(colored_status('CONFLICT', f"Both changed - rules ({len(status['conflict_rules'])}):"))
                            for rule in status['conflict_rules']:
                                print(f"   • {rule['name']} (source updated AND user modified)")
                            print()

                        if status['conflict_commands']:
                            print(colored_status('CONFLICT', f"Both changed - commands ({len(status['conflict_commands'])}):"))
                            for cmd in status['conflict_commands']:
                                print(f"   • {cmd['name']} (source updated AND user modified)")
                            print()

                        if status['missing_sources']:
                            print(colored_status('WARNING', f"Missing sources ({len(status['missing_sources'])}):"))
                            for item in status['missing_sources']:
                                print(f"   • {item['name']} ({item['type']}): {item['source']}")
                            print()

                        if status['missing_installed']:
                            print(colored_status('WARNING', f"Missing installed files ({len(status['missing_installed'])}):"))
                            for item in status['missing_installed']:
                                print(f"   • {item['name']} ({item['type']}): {item['dest']}")
                            print()

                        print(colored_status('TIP', "Use 'warden diff <project> <item>' to see changes"))
                        if status['outdated_rules'] or status['outdated_commands']:
                            print(colored_status('TIP', "Use 'warden project update <project> --all' to update outdated items"))
                        if status['user_modified_rules'] or status['user_modified_commands']:
                            print(colored_status('TIP', "User modifications will be overwritten if you update"))
                        if status['conflict_rules'] or status['conflict_commands']:
                            print(colored_status('WARNING', "Conflicts require manual resolution - backup user changes first!"))

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
                    print(colored_status('SUCCESS', 'All projects are up to date'))
                else:
                    print(colored_status('INFO', f"Found {len(all_status)} project(s) with updates:\n"))

                    for project_name, status in all_status.items():
                        if 'error' in status:
                            print(colored_status('ERROR', f"{project_name}: {status['error']}"))
                            continue

                        outdated_count = len(status.get('outdated_rules', [])) + len(status.get('outdated_commands', []))
                        modified_count = len(status.get('user_modified_rules', [])) + len(status.get('user_modified_commands', []))
                        conflict_count = len(status.get('conflict_rules', [])) + len(status.get('conflict_commands', []))
                        missing_count = len(status.get('missing_sources', []))

                        print(colored_status('UPDATE', f"{project_name}:"))
                        if outdated_count > 0:
                            print(f"   {outdated_count} outdated item(s)")
                        if modified_count > 0:
                            print(f"   {modified_count} user modified item(s)")
                        if conflict_count > 0:
                            print(f"   {conflict_count} conflict(s)")
                        if missing_count > 0:
                            print(f"   {missing_count} missing source(s)")
                        print()

                    print(colored_status('TIP', "Use 'warden status <project>' for details"))

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
