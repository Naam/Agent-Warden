"""
Tests for basic CLI commands and main() function routing.

Targets uncovered lines:
- Lines 2988-3100: main() function command routing
- Lines 3036-3044: project list command
- Lines 3046-3057: project show command
- Lines 3001-3003: no command handling
"""

import os
from unittest.mock import MagicMock, patch

from warden import main


class TestMainCommandRouting:
    """Test the main() function command routing."""

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    def test_no_command_shows_help(self, mock_updater, mock_manager):
        """Test that running with no command shows help."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        with patch('sys.argv', ['warden']):
            result = main()
            assert result == 1

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    def test_project_list_empty(self, mock_updater, mock_manager):
        """Test project list command with no projects."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        mock_manager_instance = MagicMock()
        mock_manager_instance.list_projects.return_value = []
        mock_manager.return_value = mock_manager_instance

        with patch('sys.argv', ['warden', 'project', 'list']):
            with patch('builtins.print') as mock_print:
                result = main()
                mock_print.assert_any_call("No projects registered.")
                assert result is None or result == 0

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    @patch('warden.format_project_info')
    def test_project_list_with_projects(self, mock_format, mock_updater, mock_manager):
        """Test project list command with projects."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        mock_project = MagicMock()
        mock_manager_instance = MagicMock()
        mock_manager_instance.list_projects.return_value = [mock_project]
        mock_manager.return_value = mock_manager_instance

        mock_format.return_value = "Project info"

        with patch('sys.argv', ['warden', 'project', 'list']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert any('Registered projects (1)' in str(call) for call in mock_print.call_args_list)
                assert result is None or result == 0

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    def test_project_show_not_found(self, mock_updater, mock_manager):
        """Test project show command with non-existent project."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        mock_manager_instance = MagicMock()
        mock_manager_instance.config.state = {'projects': {}}
        mock_manager.return_value = mock_manager_instance

        with patch('sys.argv', ['warden', 'project', 'show', 'nonexistent']):
            with patch('builtins.print') as mock_print:
                result = main()
                assert any("not found" in str(call).lower() for call in mock_print.call_args_list)
                assert result == 1

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    @patch('warden.format_project_detailed')
    @patch('warden.ProjectState')
    def test_project_show_success(self, mock_project_state, mock_format, mock_updater, mock_manager):
        """Test project show command with existing project."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        mock_project = MagicMock()
        mock_project_state.from_dict.return_value = mock_project

        mock_manager_instance = MagicMock()
        mock_manager_instance.config.state = {
            'projects': {
                'test-project': {'name': 'test-project'}
            }
        }
        mock_manager.return_value = mock_manager_instance

        mock_format.return_value = "Detailed project info"

        with patch('sys.argv', ['warden', 'project', 'show', 'test-project']):
            with patch('builtins.print'):
                result = main()
                mock_format.assert_called_once()
                assert result is None or result == 0

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    def test_warden_home_environment_variable(self, mock_updater, mock_manager):
        """Test that WARDEN_HOME environment variable is respected."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = False
        mock_updater.return_value = mock_updater_instance

        mock_manager_instance = MagicMock()
        mock_manager_instance.list_projects.return_value = []
        mock_manager.return_value = mock_manager_instance

        test_home = '/tmp/test-warden-home'
        with patch.dict(os.environ, {'WARDEN_HOME': test_home}):
            with patch('sys.argv', ['warden', 'project', 'list']):
                with patch('builtins.print') as mock_print:
                    main()
                    # Check that WARDEN_HOME was used
                    assert any(test_home in str(call) for call in mock_print.call_args_list)
                    mock_manager.assert_called_with(base_path=test_home)

    @patch('warden.WardenManager')
    @patch('warden.AutoUpdater')
    def test_auto_update_check_when_enabled(self, mock_updater, mock_manager):
        """Test that auto-update check runs when enabled."""
        mock_updater_instance = MagicMock()
        mock_updater_instance.should_check_for_updates.return_value = True
        mock_updater_instance.check_for_updates.return_value = {
            'commits_behind': 5,
            'latest_commit': 'abc123'
        }
        mock_updater.return_value = mock_updater_instance

        mock_manager_instance = MagicMock()
        mock_manager_instance.list_projects.return_value = []
        mock_manager.return_value = mock_manager_instance

        with patch('sys.argv', ['warden', 'project', 'list']):
            with patch('builtins.print') as mock_print:
                main()
                # Check that update message was printed
                assert any('update available' in str(call).lower() for call in mock_print.call_args_list)
                mock_updater_instance.update_last_check_time.assert_called_once()

