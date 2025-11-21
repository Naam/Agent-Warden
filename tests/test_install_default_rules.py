"""Tests for default rule installation behavior.

This test verifies that when install_project is called without specifying
rule_names, it should install all available rules by default.
"""

from pathlib import Path

from warden import WardenManager


class TestInstallDefaultRules:
    """Test cases for default rule installation."""

    def test_install_project_without_rules_installs_all_rules(self, manager: WardenManager, sample_project_dir: Path):
        """Test that install_project without rule_names installs all available rules."""
        # Get all available rules from the manager
        available_rules = manager._get_available_rules()

        # Filter out package rules (those with ':')
        built_in_rules = [r for r in available_rules if ':' not in r]

        # Verify we have some built-in rules to test with
        assert len(built_in_rules) > 0, "No built-in rules available for testing"

        # Install project without specifying rule_names (should install all rules)
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=None  # Explicitly None - should install all rules
        )

        # Verify project was created
        assert project is not None
        assert project.name == 'test_project'
        assert project.has_target('augment')

        # Verify all built-in rules were installed
        installed_rules = project.targets['augment']['installed_rules']
        installed_rule_names = [r['name'] for r in installed_rules]

        # All built-in rules should be installed
        for rule_name in built_in_rules:
            assert rule_name in installed_rule_names, f"Rule '{rule_name}' was not installed by default"

        # Verify the actual files exist
        rules_dir = sample_project_dir / ".augment" / "rules"
        assert rules_dir.exists()

        for rule_name in built_in_rules:
            rule_file = rules_dir / f"{rule_name}.md"
            assert rule_file.exists(), f"Rule file '{rule_name}.md' was not created"

    def test_install_project_with_specific_rules_only_installs_those(self, manager: WardenManager, sample_project_dir: Path):
        """Test that install_project with specific rule_names only installs those rules."""
        # Install project with specific rules
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']  # Only install these two
        )

        # Verify only the specified rules were installed
        installed_rules = project.targets['augment']['installed_rules']
        installed_rule_names = [r['name'] for r in installed_rules]

        assert len(installed_rule_names) == 2
        assert 'test-rule' in installed_rule_names
        assert 'rule1' in installed_rule_names
        assert 'test' not in installed_rule_names
        assert 'test-rule1' not in installed_rule_names

    def test_install_project_with_empty_rules_list_installs_nothing(self, manager: WardenManager, sample_project_dir: Path):
        """Test that install_project with empty rule_names list installs no rules."""
        # Install project with empty rules list
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=[]  # Empty list - should install nothing
        )

        # Verify no rules were installed
        installed_rules = project.targets['augment']['installed_rules']
        assert len(installed_rules) == 0

        # Verify has_rules is False
        assert project.targets['augment']['has_rules'] is False

    def test_install_project_default_behavior_matches_global_install(self, manager: WardenManager, sample_project_dir: Path, tmp_path: Path):
        """Test that install_project default behavior matches global-install behavior."""
        # Get all available built-in rules
        available_rules = manager._get_available_rules()
        built_in_rules = [r for r in available_rules if ':' not in r]

        # Install project without specifying rules (should install all)
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=None
        )

        installed_rules = project.targets['augment']['installed_rules']
        installed_rule_names = sorted([r['name'] for r in installed_rules])

        # Should match all built-in rules
        assert installed_rule_names == sorted(built_in_rules), \
            "Default install_project behavior should install all rules like global-install does"

