"""Tests for multi-target support."""

from pathlib import Path

import pytest

from warden import ProjectState, WardenError, WardenManager


class TestMultiTarget:
    """Test cases for multi-target support."""

    def test_install_same_project_multiple_targets(self, manager: WardenManager, sample_project_dir: Path):
        """Test installing the same project with multiple targets."""
        # Create test rules
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Install for augment
        project1 = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        assert project1.has_target('augment')
        assert len(project1.targets) == 1
        assert project1.targets['augment']['install_type'] == 'copy'
        assert project1.targets['augment']['has_rules'] is True

        # Verify augment directory was created
        augment_rules_dir = sample_project_dir / ".augment" / "rules"
        assert augment_rules_dir.exists()
        assert (augment_rules_dir / "test-rule.md").exists()

        # Install for cursor (same project path)
        project2 = manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Should be the same project with two targets
        assert project2.name == project1.name
        assert project2.has_target('augment')
        assert project2.has_target('cursor')
        assert len(project2.targets) == 2

        # Verify cursor directory was created
        cursor_rules_dir = sample_project_dir / ".cursor" / "rules"
        assert cursor_rules_dir.exists()
        assert (cursor_rules_dir / "test-rule.md").exists()

        # Verify both directories still exist
        assert (sample_project_dir / ".augment" / "rules").exists()
        assert (sample_project_dir / ".augment" / "rules" / "test-rule.md").exists()

    def test_install_duplicate_target_fails(self, manager: WardenManager, sample_project_dir: Path):
        """Test that installing the same target twice fails."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("""---
description: Test rule
---
# Test
""")

        # Install for augment
        manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Try to install augment again - should fail
        with pytest.raises(WardenError, match="already has target 'augment' installed"):
            manager.install_project(
                sample_project_dir,
                target='augment',
                use_copy=True,
                rule_names=['test-rule']
            )

    def test_add_rules_to_specific_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test adding rules to a specific target."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)

        rule1 = rules_dir / "rule1.md"
        rule1.write_text("---\ndescription: Rule 1\n---\n# Rule 1")

        rule2 = rules_dir / "rule2.md"
        rule2.write_text("---\ndescription: Rule 2\n---\n# Rule 2")

        # Install with rule1 for both targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['rule1']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['rule1']
        )

        # Add rule2 only to augment
        updated = manager.add_to_project(
            project.name,
            rule_names=['rule2'],
            target='augment'
        )

        # Check augment has both rules
        augment_rules = [r['name'] for r in updated.targets['augment']['installed_rules']]
        assert 'rule1' in augment_rules
        assert 'rule2' in augment_rules

        # Check cursor only has rule1
        cursor_rules = [r['name'] for r in updated.targets['cursor']['installed_rules']]
        assert 'rule1' in cursor_rules
        assert 'rule2' not in cursor_rules

    def test_add_rules_to_all_targets(self, manager: WardenManager, sample_project_dir: Path):
        """Test adding rules to all targets when target is not specified."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)

        rule1 = rules_dir / "rule1.md"
        rule1.write_text("---\ndescription: Rule 1\n---\n# Rule 1")

        rule2 = rules_dir / "rule2.md"
        rule2.write_text("---\ndescription: Rule 2\n---\n# Rule 2")

        # Install with rule1 for both targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['rule1']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['rule1']
        )

        # Add rule2 to all targets (no target specified)
        updated = manager.add_to_project(
            project.name,
            rule_names=['rule2']
        )

        # Check both targets have both rules
        for target_name in ['augment', 'cursor']:
            rules = [r['name'] for r in updated.targets[target_name]['installed_rules']]
            assert 'rule1' in rules
            assert 'rule2' in rules

    def test_backward_compatibility_single_target(self, manager: WardenManager):
        """Test that old single-target format is correctly loaded."""
        # Simulate old state format
        old_state_data = {
            'name': 'old-project',
            'path': '/path/to/project',
            'target': 'augment',
            'install_type': 'copy',
            'timestamp': '2024-01-01T00:00:00',
            'has_rules': True,
            'has_commands': False,
            'installed_rules': ['rule1'],
            'installed_commands': []
        }

        # Load it
        project = ProjectState.from_dict(old_state_data)

        # Should be converted to new format
        assert project.has_target('augment')
        assert len(project.targets) == 1
        assert project.targets['augment']['install_type'] == 'copy'
        assert project.targets['augment']['has_rules'] is True

    def test_remove_target_from_project(self, manager: WardenManager, sample_project_dir: Path):
        """Test removing a specific target from a multi-target project."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("---\ndescription: Test\n---\n# Test")

        # Install for both targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Reload project
        project = ProjectState.from_dict(manager.config.state['projects'][project.name])

        assert project.has_target('augment')
        assert project.has_target('cursor')

        # Remove cursor target
        removed = project.remove_target('cursor')
        assert removed is True
        assert not project.has_target('cursor')
        assert project.has_target('augment')

        # Try to remove non-existent target
        removed = project.remove_target('nonexistent')
        assert removed is False

    def test_update_specific_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test updating a specific target."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("---\ndescription: Test\n---\n# Test")

        # Install for both targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Update only augment target
        updated = manager.update_project(project.name, target='augment')

        assert updated.has_target('augment')
        assert updated.has_target('cursor')

    def test_sever_specific_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test severing a specific target from symlink to copy."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("---\ndescription: Test\n---\n# Test")

        # Install for cursor with symlink (augment always uses copy)
        project = manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=False,  # Use symlink
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Reload to get fresh state
        project = ProjectState.from_dict(manager.config.state['projects'][project.name])

        # Verify cursor is symlink, augment is copy
        assert project.targets['cursor']['install_type'] == 'symlink'
        assert project.targets['augment']['install_type'] == 'copy'

        # Sever only cursor
        severed = manager.sever_project(project.name, target='cursor', skip_confirm=True)

        # Verify cursor is now copy
        assert severed.targets['cursor']['install_type'] == 'copy'
        # Augment should still be copy
        assert severed.targets['augment']['install_type'] == 'copy'

    def test_three_targets_same_project(self, manager: WardenManager, sample_project_dir: Path):
        """Test installing three different targets to the same project."""
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("---\ndescription: Test\n---\n# Test")

        # Install for augment, cursor, and claude
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='claude',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Reload project
        project = ProjectState.from_dict(manager.config.state['projects'][project.name])

        # Verify all three targets exist
        assert len(project.targets) == 3
        assert project.has_target('augment')
        assert project.has_target('cursor')
        assert project.has_target('claude')

        # Verify directories were created
        assert (sample_project_dir / ".augment" / "rules" / "test-rule.md").exists()
        assert (sample_project_dir / ".cursor" / "rules" / "test-rule.md").exists()
        assert (sample_project_dir / ".claude" / "rules" / "test-rule.md").exists()


class TestConfigureProjectTargets:
    """Test cases for configuring default targets for a project."""

    def test_configure_project_targets_basic(self, manager: WardenManager, sample_project_dir: Path):
        """Test configuring default targets for a project."""
        # Create test rules
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Install project with multiple targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Configure default targets
        configured_project = manager.configure_project_targets(
            project.name,
            ['augment', 'cursor']
        )

        assert configured_project.default_targets == ['augment', 'cursor']
        assert configured_project.name == project.name

    def test_configure_project_targets_single_target(self, manager: WardenManager, sample_project_dir: Path):
        """Test configuring a single default target."""
        # Create test rules
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("""---
description: Test rule
---

# Test Rule
""")

        # Install project with one target
        project = manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Configure default target
        configured_project = manager.configure_project_targets(
            project.name,
            ['cursor']
        )

        assert configured_project.default_targets == ['cursor']

    def test_configure_project_targets_not_installed(self, manager: WardenManager, sample_project_dir: Path):
        """Test that configuring uninstalled targets raises an error."""
        # Create test rules
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("""---
description: Test rule
---

# Test Rule
""")

        # Install project with only augment target
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Try to configure with uninstalled target
        with pytest.raises(WardenError, match="Cannot set default targets that are not installed"):
            manager.configure_project_targets(
                project.name,
                ['augment', 'cursor']  # cursor is not installed
            )

    def test_configure_project_targets_nonexistent_project(self, manager: WardenManager):
        """Test that configuring a nonexistent project raises an error."""
        from warden import ProjectNotFoundError

        with pytest.raises(ProjectNotFoundError, match="Project 'nonexistent' not found"):
            manager.configure_project_targets('nonexistent', ['augment'])


