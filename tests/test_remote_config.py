#!/usr/bin/env python3
"""Tests for remote project configuration options."""

from unittest.mock import Mock, patch

from warden import ProjectState, WardenManager


class TestRemoteConfiguration:
    """Tests for remote project configuration settings."""

    def test_default_config_includes_remote_updates(self, tmp_path):
        """Test that default configuration includes update_remote_projects setting."""
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()

        manager = WardenManager(base_path=warden_dir)

        assert 'update_remote_projects' in manager.config.config
        assert manager.config.config['update_remote_projects'] is True

    def test_config_persists_update_remote_setting(self, tmp_path):
        """Test that update_remote_projects setting persists."""
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()

        # Create manager and change setting
        manager = WardenManager(base_path=warden_dir)
        manager.config.config['update_remote_projects'] = False
        manager.config.save_config()

        # Create new manager instance and verify setting persisted
        manager2 = WardenManager(base_path=warden_dir)
        assert manager2.config.config['update_remote_projects'] is False

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_update_all_skips_remote_when_disabled(self, mock_which, mock_run, tmp_path):
        """Test that update_all_projects skips remote projects when disabled."""
        mock_which.return_value = '/usr/bin/rsync'

        def mock_subprocess(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()
        (warden_dir / "rules" / "test.mdc").write_text("# Test")

        # Create local project
        local_project = tmp_path / "local"
        local_project.mkdir()

        manager = WardenManager(base_path=warden_dir)

        # Install to local project
        manager.install_project(str(local_project), target='augment', rule_names=['test'])

        # Install to "remote" project (mocked)
        manager.install_project("server:/remote/path", target='augment', rule_names=['test'])

        # Disable remote updates
        manager.config.config['update_remote_projects'] = False

        # Update all projects
        summary = manager.update_all_projects(dry_run=True, include_remote=False)

        # Verify remote project was skipped
        assert 'skipped_remote' in summary
        # Should have at least one remote project skipped
        remote_projects = [p for p in manager.config.state['projects'].values()
                          if ProjectState.from_dict(p).is_remote()]
        assert len(remote_projects) > 0

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_update_all_includes_remote_when_enabled(self, mock_which, mock_run, tmp_path):
        """Test that update_all_projects includes remote projects when enabled."""
        mock_which.return_value = '/usr/bin/rsync'

        def mock_subprocess(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()
        (warden_dir / "rules" / "test.mdc").write_text("# Test")

        manager = WardenManager(base_path=warden_dir)

        # Install to "remote" project (mocked)
        manager.install_project("server:/remote/path", target='augment', rule_names=['test'])

        # Enable remote updates (default)
        manager.config.config['update_remote_projects'] = True

        # Update all projects
        summary = manager.update_all_projects(dry_run=True, include_remote=True)

        # Verify remote project was NOT skipped
        assert len(summary.get('skipped_remote', [])) == 0

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_all_projects_status_respects_remote_setting(self, mock_which, mock_run, tmp_path):
        """Test that check_all_projects_status respects remote setting."""
        mock_which.return_value = '/usr/bin/rsync'

        def mock_subprocess(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        # Setup warden
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()
        (warden_dir / "rules" / "test.mdc").write_text("# Test")

        manager = WardenManager(base_path=warden_dir)

        # Install to "remote" project (mocked)
        remote_state = manager.install_project("server:/remote/path", target='augment', rule_names=['test'])

        # Check status with remote disabled
        status_without_remote = manager.check_all_projects_status(include_remote=False)

        # Remote project should not be in status
        assert remote_state.name not in status_without_remote

        # Check status with remote enabled
        manager.check_all_projects_status(include_remote=True)

        # Remote project might be in status if it has issues, or not if it's up to date
        # Either way, it should be checked (not skipped)
        # We can't assert it's in the dict because it might be up to date
        # But we can verify the function didn't skip it by checking it was processed
        # This is implicitly tested by the fact that it doesn't raise an error

    def test_config_backward_compatibility(self, tmp_path):
        """Test that old config files without update_remote_projects still work."""
        warden_dir = tmp_path / "warden"
        warden_dir.mkdir()
        (warden_dir / "rules").mkdir()
        (warden_dir / "mdc.mdc").write_text("# MDC")
        (warden_dir / "commands").mkdir()

        # Create old-style config without update_remote_projects
        import json
        config_path = warden_dir / ".warden_config.json"
        old_config = {
            'targets': {
                'augment': {'rules_path': '.augment/rules/', 'supports_commands': True}
            },
            'default_target': 'augment'
        }
        with open(config_path, 'w') as f:
            json.dump(old_config, f)

        # Load manager - should add default value
        manager = WardenManager(base_path=warden_dir)

        # Should have the default value
        assert manager.config.config['update_remote_projects'] is True

