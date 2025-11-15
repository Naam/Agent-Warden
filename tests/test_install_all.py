"""Tests for install to all projects functionality."""


import pytest

from warden import WardenError, WardenManager


class TestInstallToAllProjects:
    """Test cases for installing rules/commands to all projects."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a manager with temporary base path."""
        base_path = tmp_path / "warden"
        base_path.mkdir()
        (base_path / "commands").mkdir()
        (base_path / "packages").mkdir()
        (base_path / "rules").mkdir()

        # Create test rule files
        rules_dir = base_path / "rules"
        rules_dir.mkdir(exist_ok=True)

        rule1 = rules_dir / "rule1.md"
        rule1.write_text("---\ndescription: Test rule 1\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Rule 1")

        rule2 = rules_dir / "rule2.md"
        rule2.write_text("---\ndescription: Test rule 2\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Rule 2")

        rule3 = rules_dir / "rule3.md"
        rule3.write_text("---\ndescription: Test rule 3\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Rule 3")

        # Create test command file
        commands_dir = base_path / "commands"
        commands_dir.mkdir(exist_ok=True)

        cmd1 = commands_dir / "cmd1.md"
        cmd1.write_text("---\ndescription: Command 1\n---\n# Command 1\nTest command")

        return WardenManager(base_path)

    @pytest.fixture
    def multiple_projects(self, manager, tmp_path):
        """Create multiple installed projects."""
        projects = []

        # Create 3 projects
        for i in range(1, 4):
            project_path = tmp_path / f"project{i}"
            project_path.mkdir()

            project = manager.install_project(
                project_path,
                target='augment',
                use_copy=True,
                rule_names=['rule1']
            )
            projects.append(project)

        return projects

    def test_install_to_all_projects_rules(self, manager, multiple_projects):
        """Test installing a rule to all projects."""
        summary = manager.install_to_all_projects(
            rule_names=['rule2'],
            skip_confirm=True
        )

        # Should install to all 3 projects
        assert len(summary['installed']) == 3
        assert len(summary['errors']) == 0

        # Verify each project got the rule
        for _project_name, items in summary['installed']:
            assert 'rule2' in items['rules']

    def test_install_to_all_projects_commands(self, manager, multiple_projects):
        """Test installing a command to all projects."""
        summary = manager.install_to_all_projects(
            command_names=['cmd1'],
            skip_confirm=True
        )

        # Should install to all 3 projects
        assert len(summary['installed']) == 3
        assert len(summary['errors']) == 0

        # Verify each project got the command
        for _project_name, items in summary['installed']:
            assert 'cmd1' in items['commands']

    def test_install_to_all_projects_both(self, manager, multiple_projects):
        """Test installing both rules and commands to all projects."""
        summary = manager.install_to_all_projects(
            rule_names=['rule2'],
            command_names=['cmd1'],
            skip_confirm=True
        )

        # Should install to all 3 projects
        assert len(summary['installed']) == 3
        assert len(summary['errors']) == 0

        # Verify each project got both
        for _project_name, items in summary['installed']:
            assert 'rule2' in items['rules']
            assert 'cmd1' in items['commands']

    def test_install_to_all_projects_no_items(self, manager, multiple_projects):
        """Test that error is raised when no rules or commands specified."""
        with pytest.raises(WardenError, match="Must specify at least one rule or command"):
            manager.install_to_all_projects(skip_confirm=True)

    def test_install_to_all_projects_no_projects(self, manager):
        """Test that error is raised when no projects are registered."""
        with pytest.raises(WardenError, match="No projects registered"):
            manager.install_to_all_projects(
                rule_names=['rule1'],
                skip_confirm=True
            )

    def test_install_to_all_projects_with_target(self, manager, tmp_path):
        """Test installing to all projects with specific target."""
        # Create projects with multiple targets
        project1_path = tmp_path / "multi_project1"
        project1_path.mkdir()

        # Install with augment target
        manager.install_project(
            project1_path,
            target='augment',
            use_copy=True,
            rule_names=['rule1']
        )

        # Add cursor target to same project
        manager.install_project(
            project1_path,
            target='cursor',
            use_copy=True,
            rule_names=['rule1']
        )

        # Install rule2 to all projects, cursor target only
        summary = manager.install_to_all_projects(
            rule_names=['rule2'],
            target='cursor',
            skip_confirm=True
        )

        # Should install to cursor target
        assert len(summary['installed']) == 1
        assert len(summary['errors']) == 0

    def test_install_to_all_projects_already_installed(self, manager, multiple_projects):
        """Test installing a rule that's already installed (should skip gracefully)."""
        # rule1 is already installed in all projects
        summary = manager.install_to_all_projects(
            rule_names=['rule1'],
            skip_confirm=True
        )

        # Should still report as "installed" even though it was skipped
        assert len(summary['installed']) == 3
        assert len(summary['errors']) == 0

    def test_install_to_all_projects_partial_failure(self, manager, tmp_path):
        """Test that installation continues even if one project fails."""
        # Create two valid projects
        project1_path = tmp_path / "valid_project1"
        project1_path.mkdir()
        manager.install_project(
            project1_path,
            target='augment',
            use_copy=True,
            rule_names=['rule1']
        )

        project2_path = tmp_path / "valid_project2"
        project2_path.mkdir()
        manager.install_project(
            project2_path,
            target='augment',
            use_copy=True,
            rule_names=['rule1']
        )

        # Manually corrupt one project's path to cause an error
        # (This simulates a project with invalid path)
        project_state = manager.config.state['projects']['valid_project1']
        project_state['path'] = '/nonexistent/path/that/does/not/exist'
        manager.config.save_state()

        # Try to install to all projects
        summary = manager.install_to_all_projects(
            rule_names=['rule2'],
            skip_confirm=True
        )

        # One should succeed, one should fail
        assert len(summary['installed']) == 1  # valid_project2
        assert len(summary['errors']) == 1     # valid_project1

        # Verify the error contains the project name
        error_project, error_msg = summary['errors'][0]
        assert error_project == 'valid_project1'

    def test_install_to_all_projects_file_verification(self, manager, multiple_projects, tmp_path):
        """Test that files are actually created in all projects."""
        manager.install_to_all_projects(
            rule_names=['rule2'],
            skip_confirm=True
        )

        # Verify files exist in all projects
        for i in range(1, 4):
            project_path = tmp_path / f"project{i}"
            rule_file = project_path / ".augment" / "rules" / "rule2.md"
            assert rule_file.exists()
            assert "Test rule 2" in rule_file.read_text()

    def test_install_to_all_projects_multiple_rules(self, manager, multiple_projects):
        """Test installing multiple rules at once to all projects."""
        # Create another rule
        rule3 = manager.config.base_path / "rules" / "rule3.mdc"
        rule3.write_text("---\ndescription: Test rule 3\n---\n# Rule 3")

        summary = manager.install_to_all_projects(
            rule_names=['rule2', 'rule3'],
            skip_confirm=True
        )

        # Should install both rules to all 3 projects
        assert len(summary['installed']) == 3
        assert len(summary['errors']) == 0

        # Verify each project got both rules
        for _project_name, items in summary['installed']:
            assert 'rule2' in items['rules']
            assert 'rule3' in items['rules']

