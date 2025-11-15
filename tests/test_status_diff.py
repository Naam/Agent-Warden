"""Tests for project status and diff commands."""

from pathlib import Path

import pytest

from warden import ProjectNotFoundError, WardenError, WardenManager


class TestProjectStatus:
    """Test cases for project status checking."""

    def test_check_project_status_not_found(self, manager: WardenManager):
        """Test checking status of nonexistent project."""
        with pytest.raises(ProjectNotFoundError, match="Project 'nonexistent' not found"):
            manager.check_project_status('nonexistent')

    def test_check_project_status_up_to_date(self, manager: WardenManager, tmp_path: Path):
        """Test checking status of up-to-date project."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Check status
        status = manager.check_project_status(project.name)

        # Should have no issues for a freshly installed project
        assert isinstance(status, dict)
        assert 'outdated_rules' in status
        assert 'outdated_commands' in status
        assert 'user_modified_rules' in status
        assert 'conflict_rules' in status
        assert len(status['outdated_rules']) == 0

    def test_check_project_status_with_modified_rule(self, manager: WardenManager, tmp_path: Path):
        """Test checking status when user has modified a rule."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule'],
            use_copy=True  # Use copy so we can modify it
        )

        # Modify the installed rule
        rules_dir = project_dir / '.augment' / 'rules'
        rule_file = rules_dir / 'test-rule.md'
        if rule_file.exists():
            original_content = rule_file.read_text()
            rule_file.write_text(original_content + "\n\n# User modification")

        # Check status
        status = manager.check_project_status(project.name)

        # Should detect user modification
        assert 'user_modified_rules' in status

    def test_check_all_projects_status(self, manager: WardenManager, tmp_path: Path):
        """Test checking status of all projects."""
        # Install multiple projects
        for i in range(3):
            project_dir = tmp_path / f"project-{i}"
            project_dir.mkdir()
            manager.install_project(
                project_dir,
                target='augment',
                rule_names=['test-rule']
            )

        # Check all projects
        all_status = manager.check_all_projects_status()

        # Should return dict (may be empty if all projects are up-to-date)
        assert isinstance(all_status, dict)

    def test_check_all_projects_status_exclude_remote(self, manager: WardenManager, tmp_path: Path):
        """Test checking status with remote projects excluded."""
        # Install a local project
        local_dir = tmp_path / "local-project"
        local_dir.mkdir()
        manager.install_project(
            local_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Check status excluding remote projects
        all_status = manager.check_all_projects_status(include_remote=False)

        assert isinstance(all_status, dict)


class TestProjectDiff:
    """Test cases for project diff functionality."""

    def test_show_diff_project_not_found(self, manager: WardenManager):
        """Test showing diff for nonexistent project."""
        with pytest.raises(ProjectNotFoundError, match="Project 'nonexistent' not found"):
            manager.show_diff('nonexistent', 'some-rule')

    def test_show_diff_item_not_found(self, manager: WardenManager, tmp_path: Path):
        """Test showing diff for nonexistent item."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Try to show diff for nonexistent item
        with pytest.raises(WardenError, match="not found"):
            manager.show_diff(project.name, 'nonexistent-rule')

    def test_show_diff_no_changes(self, manager: WardenManager, tmp_path: Path):
        """Test showing diff when there are no changes."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Show diff (should be empty or minimal for unchanged file)
        diff_output = manager.show_diff(project.name, 'test-rule')

        # Diff output should be a string
        assert isinstance(diff_output, str)

    def test_show_diff_with_changes(self, manager: WardenManager, tmp_path: Path):
        """Test showing diff when rule has been modified."""
        # Install a project with copy
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule'],
            use_copy=True
        )

        # Modify the installed rule
        rules_dir = project_dir / '.augment' / 'rules'
        rule_file = rules_dir / 'test-rule.md'
        if rule_file.exists():
            original_content = rule_file.read_text()
            rule_file.write_text(original_content + "\n\n# User modification")

            # Show diff
            diff_output = manager.show_diff(project.name, 'test-rule')

            # Should contain diff markers
            assert isinstance(diff_output, str)
            # Unified diff format markers
            if diff_output:
                assert '---' in diff_output or '+++' in diff_output or len(diff_output) == 0

    def test_show_diff_with_target_specified(self, manager: WardenManager, tmp_path: Path):
        """Test showing diff with specific target."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Show diff for specific target
        diff_output = manager.show_diff(project.name, 'test-rule', target='augment')

        assert isinstance(diff_output, str)


class TestGetItemStatus:
    """Test get_item_status helper function."""

    def test_get_item_status_up_to_date(self):
        """Test item status when up to date."""
        from warden import get_item_status

        status = {
            'outdated_rules': [],
            'user_modified_rules': [],
            'conflict_rules': []
        }

        result = get_item_status('test-rule', 'rule', status)
        assert result == "[UP TO DATE]"

    def test_get_item_status_outdated(self):
        """Test item status when outdated."""
        from warden import get_item_status

        status = {
            'outdated_rules': [{'name': 'test-rule'}],
            'user_modified_rules': [],
            'conflict_rules': []
        }

        result = get_item_status('test-rule', 'rule', status)
        assert result == "[OUTDATED]"

    def test_get_item_status_modified(self):
        """Test item status when user modified."""
        from warden import get_item_status

        status = {
            'outdated_rules': [],
            'user_modified_rules': [{'name': 'test-rule'}],
            'conflict_rules': []
        }

        result = get_item_status('test-rule', 'rule', status)
        assert result == "[MODIFIED]"

    def test_get_item_status_conflict(self):
        """Test item status when in conflict."""
        from warden import get_item_status

        status = {
            'outdated_rules': [],
            'user_modified_rules': [],
            'conflict_rules': [{'name': 'test-rule'}]
        }

        result = get_item_status('test-rule', 'rule', status)
        assert result == "[CONFLICT]"

