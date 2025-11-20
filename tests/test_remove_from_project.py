"""Tests for removing rules and commands from projects."""

from pathlib import Path
from unittest.mock import patch

import pytest

from warden import ProjectNotFoundError, WardenError, WardenManager


class TestRemoveFromProject:
    """Test cases for remove_from_project functionality."""

    def test_remove_single_rule(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing a single rule from a project."""
        # Install project with multiple rules
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1', 'test']
        )

        # Verify all rules are installed
        assert len(project.targets['augment']['installed_rules']) == 3

        # Remove one rule
        with patch('builtins.input', return_value='y'):
            result = manager.remove_from_project(
                project.name,
                rule_names=['test-rule'],
                skip_confirm=False
            )

        assert 'test-rule' in result['removed_rules']
        assert len(result['removed_rules']) == 1

        # Verify rule was removed from state
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert 'test-rule' not in installed_rules
        assert 'rule1' in installed_rules
        assert 'test' in installed_rules

        # Verify file was deleted
        rule_file = sample_project_dir / ".augment" / "rules" / "test-rule.md"
        assert not rule_file.exists()

    def test_remove_multiple_rules(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing multiple rules at once."""
        # Install project with multiple rules
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1', 'test']
        )

        # Remove multiple rules
        result = manager.remove_from_project(
            project.name,
            rule_names=['test-rule', 'rule1'],
            skip_confirm=True
        )

        assert len(result['removed_rules']) == 2
        assert 'test-rule' in result['removed_rules']
        assert 'rule1' in result['removed_rules']

        # Verify only one rule remains
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert len(installed_rules) == 1
        assert 'test' in installed_rules

    def test_remove_commands(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing commands from a project."""
        # Install project with commands
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            install_commands=True,
            command_names=['test-command', 'test']
        )

        # Remove one command
        result = manager.remove_from_project(
            project.name,
            command_names=['test-command'],
            skip_confirm=True
        )

        assert 'test-command' in result['removed_commands']

        # Verify command was removed
        updated_project = manager.config.state['projects'][project.name]
        installed_commands = [c['name'] for c in updated_project['targets']['augment']['installed_commands']]
        assert 'test-command' not in installed_commands
        assert 'test' in installed_commands

        # Verify file was deleted
        command_file = sample_project_dir / ".augment" / "commands" / "test-command.md"
        assert not command_file.exists()

    def test_remove_both_rules_and_commands(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing both rules and commands in one call."""
        # Install project with both
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1'],
            install_commands=True,
            command_names=['test-command']
        )

        # Remove both
        result = manager.remove_from_project(
            project.name,
            rule_names=['test-rule'],
            command_names=['test-command'],
            skip_confirm=True
        )

        assert 'test-rule' in result['removed_rules']
        assert 'test-command' in result['removed_commands']

    def test_remove_from_specific_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing from only one target in a multi-target project."""
        # Install project with two targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        # Remove from cursor only
        result = manager.remove_from_project(
            project.name,
            rule_names=['test-rule'],
            target='cursor',
            skip_confirm=True
        )

        assert 'test-rule' in result['removed_rules']

        # Verify removed from cursor but not augment
        updated_project = manager.config.state['projects'][project.name]
        cursor_rules = [r['name'] for r in updated_project['targets']['cursor']['installed_rules']]
        augment_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]

        assert 'test-rule' not in cursor_rules
        assert 'test-rule' in augment_rules

        # Verify cursor file deleted but augment file exists
        cursor_file = sample_project_dir / ".cursor" / "rules" / "test-rule.mdc"
        augment_file = sample_project_dir / ".augment" / "rules" / "test-rule.md"
        assert not cursor_file.exists()
        assert augment_file.exists()

    def test_remove_from_all_targets(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing from all targets when target not specified."""
        # Install project with two targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        # Remove from all targets (no target specified)
        result = manager.remove_from_project(
            project.name,
            rule_names=['test-rule'],
            skip_confirm=True
        )

        assert 'test-rule' in result['removed_rules']

        # Verify removed from both targets
        updated_project = manager.config.state['projects'][project.name]
        cursor_rules = [r['name'] for r in updated_project['targets']['cursor']['installed_rules']]
        augment_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]

        assert 'test-rule' not in cursor_rules
        assert 'test-rule' not in augment_rules

        # Verify both files deleted
        cursor_file = sample_project_dir / ".cursor" / "rules" / "test-rule.mdc"
        augment_file = sample_project_dir / ".augment" / "rules" / "test-rule.md"
        assert not cursor_file.exists()
        assert not augment_file.exists()

    def test_remove_non_existent_rule(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing a rule that doesn't exist or isn't installed."""
        # Install project with one rule
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Try to remove a rule that isn't installed
        result = manager.remove_from_project(
            project.name,
            rule_names=['nonexistent-rule'],
            skip_confirm=True
        )

        # Should not error, just not remove anything
        assert 'nonexistent-rule' not in result['removed_rules']
        assert len(result['removed_rules']) == 0

    def test_remove_from_non_existent_project(self, manager: WardenManager):
        """Test error when trying to remove from non-existent project."""
        with pytest.raises(ProjectNotFoundError, match="Project 'nonexistent' not found"):
            manager.remove_from_project(
                'nonexistent',
                rule_names=['test-rule'],
                skip_confirm=True
            )

    def test_remove_without_rules_or_commands(self, manager: WardenManager, sample_project_dir: Path):
        """Test error when no rules or commands specified."""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Try to remove without specifying anything
        with pytest.raises(WardenError, match="Must specify at least one rule or command"):
            manager.remove_from_project(
                project.name,
                skip_confirm=True
            )

    def test_remove_from_non_existent_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test error when trying to remove from a target that doesn't exist."""
        # Install project with only augment target
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Try to remove from cursor target (not installed)
        with pytest.raises(WardenError, match="does not have target 'cursor'"):
            manager.remove_from_project(
                project.name,
                rule_names=['test-rule'],
                target='cursor',
                skip_confirm=True
            )

    def test_remove_with_confirmation_declined(self, manager: WardenManager, sample_project_dir: Path):
        """Test that declining confirmation cancels the removal."""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        # Mock user declining
        with patch('builtins.input', return_value='n'):
            with pytest.raises(WardenError, match="Operation cancelled by user"):
                manager.remove_from_project(
                    project.name,
                    rule_names=['test-rule'],
                    skip_confirm=False
                )

        # Verify nothing was removed
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert 'test-rule' in installed_rules
        assert 'rule1' in installed_rules

    def test_remove_updates_has_rules_flag(self, manager: WardenManager, sample_project_dir: Path):
        """Test that has_rules flag is updated when all rules removed."""
        # Install project with one rule
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        assert project.targets['augment']['has_rules'] is True

        # Remove the only rule
        manager.remove_from_project(
            project.name,
            rule_names=['test-rule'],
            skip_confirm=True
        )

        # Verify has_rules is now False
        updated_project = manager.config.state['projects'][project.name]
        assert updated_project['targets']['augment']['has_rules'] is False

