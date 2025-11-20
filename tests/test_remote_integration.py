#!/usr/bin/env python3
"""Integration tests for remote SSH functionality."""

from unittest.mock import Mock, patch

import pytest

from fs_backend import LocalBackend, RemoteBackend
from warden import WardenError, WardenManager


class TestRemoteInstallation:
    """Tests for installing to remote locations."""

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_install_to_remote_location(self, mock_which, mock_run, tmp_path):
        """Test installing rules to a remote SSH location."""
        # Setup
        mock_which.return_value = '/usr/bin/rsync'

        # Mock SSH commands
        def mock_subprocess(cmd, **kwargs):
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd

            # SSH test commands
            if 'test -e' in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")  # exists
            elif 'test -d' in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")  # is_dir
            elif 'mkdir' in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")
            elif 'rm -f' in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")
            # rsync command
            elif cmd[0] == 'rsync':
                return Mock(returncode=0, stdout="", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Create warden manager with test rules
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        rules_dir = warden_dir / "rules"
        rules_dir.mkdir()

        # Create a test rule file
        test_rule = rules_dir / "test-rule.md"
        test_rule.write_text("---\ndescription: Test Rule\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Test Rule\nThis is a test rule.")

        # Create commands directory
        commands_dir = warden_dir / "commands"
        commands_dir.mkdir()

        manager = WardenManager(base_path=warden_dir)

        # Install to remote location
        remote_location = "user@server.com:/var/www/project"
        project_state = manager.install_project(
            remote_location,
            target='augment',
            rule_names=['test-rule']
        )

        # Verify project state
        assert project_state.name == "project"
        assert project_state.location_string == remote_location
        assert project_state.is_remote() is True
        assert isinstance(project_state.backend, RemoteBackend)

        # Verify rsync was called
        rsync_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'rsync']
        assert len(rsync_calls) > 0

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_remote_requires_copy_mode(self, mock_which, mock_run, tmp_path, capsys):
        """Test that remote installations automatically use copy mode."""
        mock_which.return_value = '/usr/bin/rsync'

        def mock_subprocess(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        rules_dir = warden_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.md").write_text("---\ndescription: Test\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Test")
        (warden_dir / "commands").mkdir()

        manager = WardenManager(base_path=warden_dir)

        # Try to install with symlink mode (should be overridden)
        project_state = manager.install_project(
            "server:/remote/path",
            target='augment',
            use_copy=False,  # Request symlink
            rule_names=['test']
        )

        # Check that it was converted to copy mode
        captured = capsys.readouterr()
        assert "Remote locations require file copies" in captured.out

        # Verify install_type is copy
        target_config = project_state.get_target_config('augment')
        assert target_config['install_type'] == 'copy'

    @patch('subprocess.run')
    def test_remote_connection_error(self, mock_run, tmp_path):
        """Test handling of SSH connection errors."""
        # Mock connection refused
        mock_run.return_value = Mock(
            returncode=255,
            stdout="",
            stderr="Connection refused"
        )

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        rules_dir = warden_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.md").write_text("---\ndescription: Test\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Test")
        (warden_dir / "commands").mkdir()

        manager = WardenManager(base_path=warden_dir)

        # Try to install to unreachable remote - should get connection error
        with pytest.raises(WardenError, match="Cannot access remote location|Project path does not exist"):
            manager.install_project(
                "user@unreachable:/path",
                target='augment'
            )

    def test_local_path_still_works(self, tmp_path):
        """Test that local paths still work as before."""
        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        rules_dir = warden_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.md").write_text("---\ndescription: Test\nglobs: ['**/*.py']\nalwaysApply: true\ntype: always_apply\n---\n# Test")
        (warden_dir / "commands").mkdir()

        # Setup project
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        manager = WardenManager(base_path=warden_dir)

        # Install to local path
        project_state = manager.install_project(
            str(project_dir),
            target='augment',
            rule_names=['test']
        )

        # Verify it's local
        assert project_state.is_remote() is False
        assert isinstance(project_state.backend, LocalBackend)
        assert project_state.location_string == str(project_dir)


class TestRemoteLocationParsing:
    """Tests for remote location parsing."""

    def test_parse_remote_with_user(self):
        """Test parsing remote location with user."""
        from fs_backend import RemoteBackend, parse_location

        path, backend = parse_location("user@server.com:/var/www/app")

        assert path == "/var/www/app"
        assert isinstance(backend, RemoteBackend)
        assert backend.host == "server.com"
        assert backend.user == "user"
        assert backend.base_path == "/var/www/app"

    def test_parse_remote_without_user(self):
        """Test parsing remote location without user."""
        from fs_backend import RemoteBackend, parse_location

        path, backend = parse_location("server:/remote/path")

        assert path == "/remote/path"
        assert isinstance(backend, RemoteBackend)
        assert backend.host == "server"
        assert backend.user is None

    def test_parse_local_path(self):
        """Test parsing local path."""
        from fs_backend import LocalBackend, parse_location

        path, backend = parse_location("/local/path/to/project")

        assert path == "/local/path/to/project"
        assert isinstance(backend, LocalBackend)

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_add_to_remote_project(self, mock_which, mock_run, tmp_path):
        """Test adding rules/commands to an existing remote project."""
        mock_which.return_value = '/usr/bin/rsync'

        def mock_subprocess(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        rules_dir = warden_dir / "rules"
        rules_dir.mkdir()

        # Create test rules
        (rules_dir / "rule1.md").write_text("---\ndescription: Rule 1\n---\n# Rule 1")
        (rules_dir / "rule2.md").write_text("---\ndescription: Rule 2\n---\n# Rule 2")

        commands_dir = warden_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "cmd1.md").write_text("---\ndescription: Command 1\n---\n# Command 1")

        manager = WardenManager(base_path=warden_dir)

        # Install initial project to remote
        remote_location = "user@server.com:/var/www/project"
        project_state = manager.install_project(
            remote_location,
            target='augment',
            rule_names=['rule1']
        )

        assert project_state.is_remote()
        assert 'rule1' in [r['name'] for r in project_state.targets['augment']['installed_rules']]

        # Now add more rules and commands using add_to_project
        updated_project = manager.add_to_project(
            project_state.name,
            rule_names=['rule2'],
            command_names=['cmd1']
        )

        # Verify the additions
        assert updated_project.is_remote()
        assert 'rule1' in [r['name'] for r in updated_project.targets['augment']['installed_rules']]
        assert 'rule2' in [r['name'] for r in updated_project.targets['augment']['installed_rules']]
        assert 'cmd1' in [c['name'] for c in updated_project.targets['augment']['installed_commands']]

        # Verify rsync was called for the new files
        rsync_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'rsync']
        assert len(rsync_calls) > 0

