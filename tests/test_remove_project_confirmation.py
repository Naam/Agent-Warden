"""
Test remove_project confirmation logic.

Targets uncovered lines 1354-1363 in warden.py.
"""

from unittest.mock import patch


class TestRemoveProjectConfirmation:
    """Test interactive confirmation when removing projects."""

    def test_remove_project_user_confirms_removal(self, manager, sample_project_dir):
        """User confirming removal proceeds with deletion."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Mock user input to confirm
        with patch('builtins.input', return_value='y'):
            result = manager.remove_project(project.name, skip_confirm=False)

        # Verify project was removed
        assert result is True
        assert project.name not in manager.config.state['projects']

    def test_remove_project_user_declines_removal(self, manager, sample_project_dir):
        """User declining removal keeps the project."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Mock user input to decline
        with patch('builtins.input', return_value='n'):
            result = manager.remove_project(project.name, skip_confirm=False)

        # Verify project was NOT removed
        assert result is False
        assert project.name in manager.config.state['projects']

    def test_remove_project_user_types_yes(self, manager, sample_project_dir):
        """User typing 'yes' removes the project."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Mock user input to type 'yes'
        with patch('builtins.input', return_value='yes'):
            result = manager.remove_project(project.name, skip_confirm=False)

        # Verify project was removed
        assert result is True
        assert project.name not in manager.config.state['projects']

    def test_remove_project_skip_confirm_removes_immediately(self, manager, sample_project_dir):
        """Skipping confirmation removes project without prompt."""
        # Create a project
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Remove with skip_confirm=True (no input mock needed)
        result = manager.remove_project(project.name, skip_confirm=True)

        # Verify project was removed
        assert result is True
        assert project.name not in manager.config.state['projects']

    def test_remove_nonexistent_project_returns_false(self, manager):
        """Removing non-existent project returns False."""
        # Try to remove project that doesn't exist
        result = manager.remove_project('nonexistent', skip_confirm=True)

        # Verify returns False
        assert result is False

