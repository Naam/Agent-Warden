"""
Test CLI main function by invoking it with different arguments.

Targets uncovered CLI code in main() function (lines 3210-3832).
"""

from unittest.mock import patch

from warden import main


class TestCLIStatus:
    """Test status command via CLI main()."""

    def test_status_command_shows_all_projects(self, manager, sample_project_dir, capsys):
        """Status command displays all projects."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run status command via CLI
        with patch('sys.argv', ['warden', 'status']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        # Verify command executed successfully
        assert result is None or result == 0

        # Verify output contains project info
        captured = capsys.readouterr()
        assert project.name in captured.out or 'up to date' in captured.out.lower()

    def test_status_specific_project(self, manager, sample_project_dir, capsys):
        """Status command for specific project."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Run status for specific project
        with patch('sys.argv', ['warden', 'status', project.name]):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0


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

