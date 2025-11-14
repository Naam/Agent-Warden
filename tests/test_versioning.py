"""Tests for checksum-based versioning features."""

from pathlib import Path

import pytest

from warden import WardenManager


class TestVersioning:
    """Test checksum-based versioning and status checking."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a manager with temporary base path."""
        base_path = tmp_path / "warden"
        base_path.mkdir()
        (base_path / "commands").mkdir()
        (base_path / "packages").mkdir()
        (base_path / "rules").mkdir()

        # Create required mdc.mdc file
        mdc_file = base_path / "mdc.mdc"
        mdc_file.write_text("---\ndescription: MDC format\n---\n")

        # Create a test rule file
        rule_file = base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Test rule\n---\n# Test")

        return WardenManager(base_path)

    @pytest.fixture
    def installed_project(self, manager, tmp_path):
        """Create an installed project with a rule."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Install the project
        project = manager.install_project(
            project_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        return project

    def test_check_status_up_to_date(self, manager, installed_project):
        """Test status check when everything is up to date."""
        status = manager.check_project_status(installed_project.name)

        assert len(status['outdated_rules']) == 0
        assert len(status['outdated_commands']) == 0
        assert len(status['user_modified_rules']) == 0
        assert len(status['user_modified_commands']) == 0
        assert len(status['conflict_rules']) == 0
        assert len(status['conflict_commands']) == 0

    def test_check_status_source_updated(self, manager, installed_project, tmp_path):
        """Test status check when source file is updated."""
        # Update the source file
        rule_file = manager.config.base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Test rule updated\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['outdated_rules']) == 1
        assert status['outdated_rules'][0]['name'] == 'test-rule'
        assert len(status['user_modified_rules']) == 0

    def test_check_status_user_modified(self, manager, installed_project, tmp_path):
        """Test status check when user modifies installed file."""
        # Modify the installed file
        project_path = Path(installed_project.path)
        installed_file = project_path / ".augment" / "rules" / "test-rule.mdc"
        installed_file.write_text("---\ndescription: User modified\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['user_modified_rules']) == 1
        assert status['user_modified_rules'][0]['name'] == 'test-rule'
        assert len(status['outdated_rules']) == 0

    def test_check_status_conflict(self, manager, installed_project, tmp_path):
        """Test status check when both source and installed are modified."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Source updated\n---\n# Test")

        # Modify installed
        project_path = Path(installed_project.path)
        installed_file = project_path / ".augment" / "rules" / "test-rule.mdc"
        installed_file.write_text("---\ndescription: User modified\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['conflict_rules']) == 1
        assert status['conflict_rules'][0]['name'] == 'test-rule'
        assert len(status['outdated_rules']) == 0
        assert len(status['user_modified_rules']) == 0

    def test_update_project_items_specific_rule(self, manager, installed_project, tmp_path):
        """Test updating a specific rule."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test")

        # Update the rule
        result = manager.update_project_items(
            installed_project.name,
            rule_names=['test-rule']
        )

        assert len(result['rules']) == 1
        assert 'test-rule' in result['rules']
        assert len(result['errors']) == 0

        # Verify it's now up to date
        status = manager.check_project_status(installed_project.name)
        assert len(status['outdated_rules']) == 0

    def test_update_project_items_all(self, manager, installed_project, tmp_path):
        """Test updating all outdated items."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test")

        # Update all
        result = manager.update_project_items(
            installed_project.name,
            update_all=True
        )

        assert len(result['rules']) == 1
        assert 'test-rule' in result['rules']

    def test_show_diff(self, manager, installed_project, tmp_path):
        """Test showing diff between installed and current version."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.mdc"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test Updated")

        # Get diff
        diff = manager.show_diff(installed_project.name, 'test-rule')

        assert 'Test rule' in diff or 'Updated version' in diff
        assert '---' in diff or '+++' in diff

