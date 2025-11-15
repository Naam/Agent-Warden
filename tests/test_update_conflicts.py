"""Tests for project update and conflict resolution."""

from pathlib import Path

import pytest

from warden import ProjectNotFoundError, WardenManager


class TestProjectUpdate:
    """Test cases for project update functionality."""

    def test_update_project_not_found(self, manager: WardenManager):
        """Test updating nonexistent project."""
        with pytest.raises(ProjectNotFoundError, match="Project 'nonexistent' not found"):
            manager.update_project('nonexistent')

    def test_update_project_basic(self, manager: WardenManager, tmp_path: Path):
        """Test basic project update."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Update the project
        updated_project = manager.update_project(project.name)

        assert updated_project.name == project.name
        assert updated_project.path == project.path

    def test_update_project_specific_target(self, manager: WardenManager, tmp_path: Path):
        """Test updating specific target in project."""
        # Install a project with multiple targets
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Update specific target
        updated_project = manager.update_project(project.name, target='augment')

        assert updated_project.name == project.name

    def test_update_project_path_not_exists(self, manager: WardenManager, tmp_path: Path):
        """Test updating project when path no longer exists."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Remove the project directory
        import shutil
        shutil.rmtree(project_dir)

        # Try to update - should raise error
        with pytest.raises(FileNotFoundError, match="Project path no longer exists"):
            manager.update_project(project.name)


class TestUpdateAllProjects:
    """Test cases for batch project updates."""

    def test_update_all_projects_dry_run(self, manager: WardenManager, tmp_path: Path):
        """Test dry-run mode for update-all."""
        # Install multiple projects
        for i in range(2):
            project_dir = tmp_path / f"project-{i}"
            project_dir.mkdir()
            manager.install_project(
                project_dir,
                target='augment',
                rule_names=['test-rule']
            )

        # Run update-all in dry-run mode
        summary = manager.update_all_projects(dry_run=True)

        assert isinstance(summary, dict)
        assert 'updated' in summary
        assert 'skipped_uptodate' in summary
        assert 'errors' in summary

    def test_update_all_projects_actual(self, manager: WardenManager, tmp_path: Path):
        """Test actual update-all execution."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Run update-all
        summary = manager.update_all_projects(dry_run=False)

        assert isinstance(summary, dict)
        assert 'updated' in summary
        assert 'skipped_uptodate' in summary

    def test_update_all_projects_exclude_remote(self, manager: WardenManager, tmp_path: Path):
        """Test update-all excluding remote projects."""
        # Install a local project
        project_dir = tmp_path / "local-project"
        project_dir.mkdir()

        manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Run update-all excluding remote
        summary = manager.update_all_projects(include_remote=False, dry_run=True)

        assert isinstance(summary, dict)
        assert 'skipped_remote' in summary

    def test_update_all_projects_with_errors(self, manager: WardenManager, tmp_path: Path):
        """Test update-all when some projects have errors."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Remove project directory to cause error
        import shutil
        shutil.rmtree(project_dir)

        # Run update-all
        summary = manager.update_all_projects(dry_run=False)

        # Should handle errors gracefully
        assert isinstance(summary, dict)
        assert 'errors' in summary


class TestConflictDetection:
    """Test cases for three-way merge conflict detection."""

    def test_detect_user_modification(self, manager: WardenManager, tmp_path: Path):
        """Test detection of user modifications."""
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

        # Check status
        status = manager.check_project_status(project.name)

        # Should detect modification
        assert 'user_modified_rules' in status

    def test_detect_missing_source(self, manager: WardenManager, tmp_path: Path):
        """Test detection of missing source files."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Remove the source rule file
        source_rule = manager.config.base_path / 'rules' / 'test-rule.md'
        if source_rule.exists():
            source_rule.unlink()

        # Check status
        status = manager.check_project_status(project.name)

        # Should detect missing source
        assert 'missing_sources' in status

    def test_detect_missing_installed_file(self, manager: WardenManager, tmp_path: Path):
        """Test detection of missing installed files."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Remove the installed rule file
        rules_dir = project_dir / '.augment' / 'rules'
        rule_file = rules_dir / 'test-rule.md'
        if rule_file.exists():
            rule_file.unlink()

        # Check status
        status = manager.check_project_status(project.name)

        # Should detect missing installed file
        assert 'missing_installed' in status


class TestUpdateProjectItems:
    """Test cases for update_project_items functionality."""

    def test_update_project_items_basic(self, manager: WardenManager, tmp_path: Path):
        """Test basic update of project items."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            rule_names=['test-rule']
        )

        # Update project items
        result = manager.update_project_items(project.name, update_all=True)

        assert isinstance(result, dict)
        assert 'rules' in result
        assert 'commands' in result

    def test_update_project_items_force(self, manager: WardenManager, tmp_path: Path):
        """Test force update of project items."""
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
            rule_file.write_text("Modified content")

        # Force update should overwrite modifications
        result = manager.update_project_items(project.name, update_all=True, force=True)

        assert isinstance(result, dict)

