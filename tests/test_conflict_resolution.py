"""
Test conflict resolution confirmation logic.

Targets uncovered lines 2234-2251 in warden.py (update_project_items conflict handling).
"""

from unittest.mock import patch


class TestConflictResolution:
    """Test interactive confirmation when resolving conflicts during updates."""

    def test_conflict_user_confirms_overwrite(self, manager, sample_project_dir):
        """User confirming conflict resolution overwrites local changes."""
        # Create a project with a rule
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Modify the installed rule to create a conflict
        target_rule = sample_project_dir / '.augment' / 'rules' / 'test-rule.md'
        original_content = target_rule.read_text()
        target_rule.write_text(original_content + "\n# Local modification")

        # Update the source rule to create a conflict
        source_rule = manager.config.rules_dir / 'test-rule.md'
        source_rule.write_text(original_content + "\n# Source update")

        # Mock user input to confirm overwrite
        with patch('builtins.input', return_value='y'):
            result = manager.update_project_items(
                project.name,
                rule_names=['test-rule'],
                force=False,
                skip_confirm=False
            )

        # Verify rule was updated (not skipped)
        assert 'test-rule' in result['rules']
        assert 'test-rule' not in result.get('skipped', [])

    def test_conflict_user_declines_overwrite(self, manager, sample_project_dir):
        """User declining conflict resolution skips the update."""
        # Create a project with a rule
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Modify the installed rule to create a conflict
        target_rule = sample_project_dir / '.augment' / 'rules' / 'test-rule.md'
        original_content = target_rule.read_text()
        target_rule.write_text(original_content + "\n# Local modification")

        # Update the source rule to create a conflict
        source_rule = manager.config.rules_dir / 'test-rule.md'
        source_rule.write_text(original_content + "\n# Source update")

        # Mock user input to decline overwrite
        with patch('builtins.input', return_value='n'):
            result = manager.update_project_items(
                project.name,
                rule_names=['test-rule'],
                force=False,
                skip_confirm=False
            )

        # Verify rule was skipped (not updated)
        assert 'test-rule' not in result['rules']
        assert 'test-rule' in result.get('skipped', [])

    def test_conflict_skip_confirm_without_force_skips(self, manager, sample_project_dir):
        """Skip confirm without force skips conflicts."""
        # Create a project with a rule
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Modify the installed rule to create a conflict
        target_rule = sample_project_dir / '.augment' / 'rules' / 'test-rule.md'
        original_content = target_rule.read_text()
        target_rule.write_text(original_content + "\n# Local modification")

        # Update the source rule to create a conflict
        source_rule = manager.config.rules_dir / 'test-rule.md'
        source_rule.write_text(original_content + "\n# Source update")

        # Update with skip_confirm=True but force=False
        result = manager.update_project_items(
            project.name,
            rule_names=['test-rule'],
            force=False,
            skip_confirm=True
        )

        # Verify rule was skipped (not updated)
        assert 'test-rule' not in result['rules']
        assert 'test-rule' in result.get('skipped', [])

    def test_conflict_with_force_overwrites(self, manager, sample_project_dir):
        """Force flag overwrites conflicts without prompting."""
        # Create a project with a rule
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Modify the installed rule to create a conflict
        target_rule = sample_project_dir / '.augment' / 'rules' / 'test-rule.md'
        original_content = target_rule.read_text()
        target_rule.write_text(original_content + "\n# Local modification")

        # Update the source rule to create a conflict
        source_rule = manager.config.rules_dir / 'test-rule.md'
        source_rule.write_text(original_content + "\n# Source update")

        # Update with force=True (no input mock needed)
        result = manager.update_project_items(
            project.name,
            rule_names=['test-rule'],
            force=True,
            skip_confirm=False
        )

        # Verify rule was updated (not skipped)
        assert 'test-rule' in result['rules']
        assert 'test-rule' not in result.get('skipped', [])

