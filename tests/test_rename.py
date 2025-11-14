"""Tests for project rename functionality."""

from pathlib import Path

import pytest

from warden import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
    WardenManager,
)


class TestProjectRename:
    """Test cases for project rename functionality."""

    def test_rename_project_success(self, manager: WardenManager, sample_project_dir: Path):
        """Test successful project rename."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Install project with original name
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        original_name = project.name
        assert original_name in manager.config.state['projects']

        # Rename the project
        renamed_project = manager.rename_project(original_name, 'new-name')

        # Verify rename
        assert renamed_project.name == 'new-name'
        assert 'new-name' in manager.config.state['projects']
        assert original_name not in manager.config.state['projects']
        assert renamed_project.path == project.path
        # Check targets are preserved
        assert renamed_project.has_target('augment')
        assert renamed_project.targets == project.targets

    def test_rename_project_not_found(self, manager: WardenManager):
        """Test renaming a non-existent project."""
        with pytest.raises(ProjectNotFoundError):
            manager.rename_project('nonexistent', 'new-name')

    def test_rename_project_name_conflict(self, manager: WardenManager, temp_dir: Path):
        """Test renaming to an existing project name."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Create two projects
        project1_dir = temp_dir / "project1"
        project1_dir.mkdir()
        project2_dir = temp_dir / "project2"
        project2_dir.mkdir()

        manager.install_project(project1_dir, target='augment', use_copy=True, rule_names=['test-rule'])
        manager.install_project(project2_dir, target='augment', use_copy=True, rule_names=['test-rule'])

        # Try to rename project1 to project2 (should fail)
        with pytest.raises(ProjectAlreadyExistsError):
            manager.rename_project('project1', 'project2')

    def test_rename_project_empty_name(self, manager: WardenManager, sample_project_dir: Path):
        """Test renaming with empty name."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        with pytest.raises(WardenError):
            manager.rename_project(project.name, '')

        with pytest.raises(WardenError):
            manager.rename_project(project.name, '   ')

    def test_install_with_custom_name(self, manager: WardenManager, sample_project_dir: Path):
        """Test installing project with custom name."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Install with custom name
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule'],
            custom_name='my-custom-project'
        )

        # Verify custom name was used
        assert project.name == 'my-custom-project'
        assert 'my-custom-project' in manager.config.state['projects']
        assert sample_project_dir.name not in manager.config.state['projects']

    def test_add_to_existing_project(self, manager: WardenManager, sample_project_dir: Path):
        """Test adding rules/commands to existing project."""
        # Create rules directory with test rules
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)

        test_rule1 = rules_dir / "test-rule1.mdc"
        test_rule1.write_text("""---
description: Test rule 1
globs: ["**/*.py"]
---

# Test Rule 1
This is test rule 1.
""")

        test_rule2 = rules_dir / "test-rule2.mdc"
        test_rule2.write_text("""---
description: Test rule 2
globs: ["**/*.js"]
---

# Test Rule 2
This is test rule 2.
""")

        # Install project with one rule
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule1']
        )

        assert len(project.targets['augment']['installed_rules']) == 1
        assert project.targets['augment']['installed_rules'][0]['name'] == 'test-rule1'

        # Add another rule to existing project
        updated_project = manager.add_to_project(project.name, rule_names=['test-rule2'])

        assert len(updated_project.targets['augment']['installed_rules']) == 2
        rule_names = [r['name'] for r in updated_project.targets['augment']['installed_rules']]
        assert 'test-rule1' in rule_names
        assert 'test-rule2' in rule_names

    def test_add_to_project_skip_duplicates(self, manager: WardenManager, sample_project_dir: Path):
        """Test that adding duplicate rules/commands is skipped."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Install project with rule
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        initial_count = len(project.targets['augment']['installed_rules'])

        # Try to add the same rule again
        updated_project = manager.add_to_project(project.name, rule_names=['test-rule'])

        # Should still have the same count (duplicate skipped)
        assert len(updated_project.targets['augment']['installed_rules']) == initial_count

    def test_add_to_nonexistent_project(self, manager: WardenManager):
        """Test adding to non-existent project."""
        with pytest.raises(ProjectNotFoundError):
            manager.add_to_project('nonexistent', rule_names=['test-rule'])

    def test_install_with_whitespace_custom_name(self, manager: WardenManager, sample_project_dir: Path):
        """Test installing with whitespace-only custom name raises error."""
        # Create rules directory with a test rule
        rules_dir = manager.config.base_path / "rules"
        rules_dir.mkdir(exist_ok=True)
        test_rule = rules_dir / "test-rule.mdc"
        test_rule.write_text("""---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
This is a test rule.
""")

        # Whitespace-only name should raise error
        with pytest.raises(WardenError, match="Custom project name cannot be empty"):
            manager.install_project(
                sample_project_dir,
                target='augment',
                use_copy=True,
                rule_names=['test-rule'],
                custom_name='   '
            )

        # Empty string falls back to directory name (this is acceptable behavior)
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule'],
            custom_name=''
        )
        assert project.name == sample_project_dir.name

