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

        # Create a test rule file
        rule_file = base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Test rule\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Test")

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
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Test rule updated\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['outdated_rules']) == 1
        assert status['outdated_rules'][0]['name'] == 'test-rule'
        assert len(status['user_modified_rules']) == 0

    def test_check_status_user_modified(self, manager, installed_project, tmp_path):
        """Test status check when user modifies installed file."""
        # Modify the installed file
        project_path = Path(installed_project.path)
        installed_file = project_path / ".augment" / "rules" / "test-rule.md"
        installed_file.write_text("---\ndescription: User modified\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['user_modified_rules']) == 1
        assert status['user_modified_rules'][0]['name'] == 'test-rule'
        assert len(status['outdated_rules']) == 0

    def test_check_status_conflict(self, manager, installed_project, tmp_path):
        """Test status check when both source and installed are modified."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Source updated\n---\n# Test")

        # Modify installed
        project_path = Path(installed_project.path)
        installed_file = project_path / ".augment" / "rules" / "test-rule.md"
        installed_file.write_text("---\ndescription: User modified\n---\n# Test")

        status = manager.check_project_status(installed_project.name)

        assert len(status['conflict_rules']) == 1
        assert status['conflict_rules'][0]['name'] == 'test-rule'
        assert len(status['outdated_rules']) == 0
        assert len(status['user_modified_rules']) == 0

    def test_update_project_items_specific_rule(self, manager, installed_project, tmp_path):
        """Test updating a specific rule."""
        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
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
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
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
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test Updated")

        # Get diff
        diff = manager.show_diff(installed_project.name, 'test-rule')

        assert 'Test rule' in diff or 'Updated version' in diff
        assert '---' in diff or '+++' in diff

    def test_update_all_projects_with_outdated(self, manager, tmp_path):
        """Test updating all projects when multiple have outdated items."""
        # Create two projects with rules
        project1_path = tmp_path / "project1"
        project1_path.mkdir()
        project2_path = tmp_path / "project2"
        project2_path.mkdir()

        # Install both projects
        project1 = manager.install_project(
            project1_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )
        project2 = manager.install_project(
            project2_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Update the source rule
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test Updated")

        # Update all projects
        summary = manager.update_all_projects(dry_run=False)

        # Both projects should be updated
        assert len(summary['updated']) == 2
        updated_names = [name for name, _ in summary['updated']]
        assert project1.name in updated_names
        assert project2.name in updated_names

        # Verify both were actually updated
        for _name, items in summary['updated']:
            assert 'test-rule' in items['rules']

        # No conflicts or errors
        assert len(summary['skipped_conflicts']) == 0
        assert len(summary['errors']) == 0

    def test_update_all_projects_skip_conflicts(self, manager, tmp_path):
        """Test that projects with conflicts are skipped."""
        # Create project with rule
        project_path = tmp_path / "project_conflict"
        project_path.mkdir()

        project = manager.install_project(
            project_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Modify source file
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Updated source\n---\n# Source Updated")

        # Modify installed file (different from both original and new source)
        installed_file = project_path / ".augment" / "rules" / "test-rule.md"
        installed_file.write_text("---\ndescription: User modified\n---\n# User Modified")

        # Update all projects
        summary = manager.update_all_projects(dry_run=False)

        # Project should be skipped due to conflict
        assert len(summary['skipped_conflicts']) == 1
        assert summary['skipped_conflicts'][0][0] == project.name
        conflicts = summary['skipped_conflicts'][0][1]
        assert 'test-rule' in conflicts['rules']

        # No projects updated
        assert len(summary['updated']) == 0

    def test_update_all_projects_skip_uptodate(self, manager, tmp_path):
        """Test that up-to-date projects are skipped."""
        # Create project with rule
        project_path = tmp_path / "project_uptodate"
        project_path.mkdir()

        project = manager.install_project(
            project_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Don't modify anything - project is up to date
        summary = manager.update_all_projects(dry_run=False)

        # Project should be skipped as up to date
        assert len(summary['skipped_uptodate']) == 1
        assert project.name in summary['skipped_uptodate']

        # No updates or conflicts
        assert len(summary['updated']) == 0
        assert len(summary['skipped_conflicts']) == 0

    def test_update_all_projects_dry_run(self, manager, tmp_path):
        """Test dry run mode doesn't actually update."""
        # Create project with rule
        project_path = tmp_path / "project_dryrun"
        project_path.mkdir()

        project = manager.install_project(
            project_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Update source
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Updated version\n---\n# Test Updated")

        # Get original installed content
        installed_file = project_path / ".augment" / "rules" / "test-rule.md"
        original_installed = installed_file.read_text()

        # Dry run
        summary = manager.update_all_projects(dry_run=True)

        # Should show what would be updated
        assert len(summary['updated']) == 1
        assert summary['updated'][0][0] == project.name
        assert 'test-rule' in summary['updated'][0][1]['rules']

        # But file should NOT be actually updated
        assert installed_file.read_text() == original_installed

    def test_update_all_projects_mixed_scenarios(self, manager, tmp_path):
        """Test update with mix of outdated, up-to-date, and conflict projects."""
        # Create three projects
        outdated_path = tmp_path / "outdated"
        outdated_path.mkdir()
        uptodate_path = tmp_path / "uptodate"
        uptodate_path.mkdir()
        conflict_path = tmp_path / "conflict"
        conflict_path.mkdir()

        # Install all three
        outdated = manager.install_project(
            outdated_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )
        uptodate = manager.install_project(
            uptodate_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )
        conflict = manager.install_project(
            conflict_path,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Update source (makes outdated and conflict outdated)
        rule_file = manager.config.base_path / "rules" / "test-rule.md"
        rule_file.write_text("---\ndescription: Updated source\n---\n# Source Updated")

        # Modify conflict project's installed file (different from both original and new source)
        conflict_file = conflict_path / ".augment" / "rules" / "test-rule.md"
        conflict_file.write_text("---\ndescription: User modified\n---\n# User Modified")

        # Update uptodate project to match source (make it up to date)
        uptodate_file = uptodate_path / ".augment" / "rules" / "test-rule.md"
        uptodate_file.write_text(rule_file.read_text())
        # Update checksum in state
        uptodate_state = manager.config.state['projects'][uptodate.name]
        from agent_warden.utils import calculate_file_checksum
        new_checksum = calculate_file_checksum(rule_file)
        uptodate_state['targets']['augment']['installed_rules'][0]['checksum'] = new_checksum
        manager.config.save_state()

        # Update all
        summary = manager.update_all_projects(dry_run=False)

        # Verify results
        assert len(summary['updated']) == 1
        assert summary['updated'][0][0] == outdated.name

        assert len(summary['skipped_conflicts']) == 1
        assert summary['skipped_conflicts'][0][0] == conflict.name

        assert len(summary['skipped_uptodate']) == 1
        assert uptodate.name in summary['skipped_uptodate']

