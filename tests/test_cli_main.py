"""
Test CLI main function by invoking it with different arguments.

Targets uncovered CLI code in main() function (lines 3210-3832).
"""

from unittest.mock import patch

from warden import main


class TestCLIStatus:
    """Test status command via CLI main()."""

    def test_status_command_shows_all_projects(self, manager, sample_project_dir, capsys):
        """Status command displays all projects (default when no command given)."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run status command via CLI (no command = status)
        with patch('sys.argv', ['warden']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        # Verify command executed successfully
        assert result is None or result == 0

        # Verify output contains project info
        captured = capsys.readouterr()
        assert project.name in captured.out or 'up to date' in captured.out.lower()

    def test_status_specific_project(self, manager, sample_project_dir, capsys):
        """Status command for specific project (warden <project-name>)."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run status for specific project (warden <project-name>)
        with patch('sys.argv', ['warden', project.name]):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

    def test_warden_without_args_shows_status(self, manager, sample_project_dir, capsys):
        """Test that 'warden' without arguments shows status for all projects."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run warden without any arguments
        with patch('sys.argv', ['warden']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        # Verify command executed successfully
        assert result is None or result == 0

        # Verify output contains status information
        captured = capsys.readouterr()
        # Should show either project name or "up to date" message
        assert project.name in captured.out or 'up to date' in captured.out.lower()

    def test_warden_with_project_name_shows_project_status(self, manager, sample_project_dir, capsys):
        """Test that 'warden <project-name>' shows status for that project."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run warden with project name
        with patch('sys.argv', ['warden', project.name]):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        # Verify command executed successfully
        assert result is None or result == 0

        # Verify output contains project-specific status
        captured = capsys.readouterr()
        assert project.name in captured.out or 'Status for project' in captured.out

    def test_status_subcommand_no_longer_exists(self, capsys):
        """Test that 'warden status' is now interpreted as checking project named 'status'."""
        # Run warden status command (now interpreted as project name)
        with patch('sys.argv', ['warden', 'status']):
            result = main()

        # Should fail because project 'status' doesn't exist
        assert result == 1

        # Verify error message says project not found
        captured = capsys.readouterr()
        assert 'not found' in captured.out or 'not found' in captured.err


class TestCLIInfo:
    """Test info commands via CLI main()."""

    def test_show_project_command(self, manager, sample_project_dir, capsys):
        """Show command displays project information."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run show command
        with patch('sys.argv', ['warden', 'project', 'show', project.name]):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        # Verify output contains project details
        captured = capsys.readouterr()
        assert project.name in captured.out




class TestCLIList:
    """Test list commands via CLI main()."""

    def test_list_projects_command(self, manager, sample_project_dir, capsys):
        """List projects command displays all projects."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run list command
        with patch('sys.argv', ['warden', 'project', 'list']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        # Verify output contains project
        captured = capsys.readouterr()
        assert project.name in captured.out

    def test_list_commands_command(self, manager, capsys):
        """List-commands command displays available commands."""
        # Run list-commands command
        with patch('sys.argv', ['warden', 'list-commands']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        # Verify output contains commands
        captured = capsys.readouterr()
        assert 'test-command' in captured.out or 'command' in captured.out.lower()

    def test_search_command(self, manager, capsys):
        """Search command finds rules and commands."""
        # Run search command
        with patch('sys.argv', ['warden', 'search', 'test']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        # Verify output contains search results
        captured = capsys.readouterr()
        assert 'test' in captured.out.lower() or 'found' in captured.out.lower()

