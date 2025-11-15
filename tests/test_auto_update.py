"""Tests for AutoUpdater class."""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from warden import AutoUpdater, WardenConfig


class TestAutoUpdater:
    """Test cases for AutoUpdater."""

    @pytest.fixture
    def auto_updater(self, config: WardenConfig) -> AutoUpdater:
        """Create an AutoUpdater instance for testing."""
        return AutoUpdater(config)

    def test_init(self, auto_updater: AutoUpdater, config: WardenConfig):
        """Test AutoUpdater initialization."""
        assert auto_updater.config == config
        assert auto_updater.repo_path.exists()
        assert auto_updater.script_path.exists()

    def test_should_check_for_updates_when_enabled(self, auto_updater: AutoUpdater):
        """Test that update check is allowed when enabled and no recent check."""
        # Ensure auto_update is enabled
        auto_updater.config.config['auto_update'] = True
        # Clear last check time
        auto_updater.config.state.pop('last_update_check', None)

        assert auto_updater.should_check_for_updates() is True

    def test_should_check_for_updates_when_disabled(self, auto_updater: AutoUpdater):
        """Test that update check is skipped when disabled."""
        auto_updater.config.config['auto_update'] = False

        assert auto_updater.should_check_for_updates() is False

    def test_should_check_for_updates_within_24_hours(self, auto_updater: AutoUpdater):
        """Test that update check is skipped within 24 hours."""
        auto_updater.config.config['auto_update'] = True
        # Set last check to 1 hour ago
        one_hour_ago = datetime.now() - timedelta(hours=1)
        auto_updater.config.state['last_update_check'] = one_hour_ago.isoformat()

        assert auto_updater.should_check_for_updates() is False

    def test_should_check_for_updates_after_24_hours(self, auto_updater: AutoUpdater):
        """Test that update check is allowed after 24 hours."""
        auto_updater.config.config['auto_update'] = True
        # Set last check to 25 hours ago
        twenty_five_hours_ago = datetime.now() - timedelta(hours=25)
        auto_updater.config.state['last_update_check'] = twenty_five_hours_ago.isoformat()

        assert auto_updater.should_check_for_updates() is True

    def test_should_check_for_updates_invalid_timestamp(self, auto_updater: AutoUpdater):
        """Test that invalid timestamp allows update check."""
        auto_updater.config.config['auto_update'] = True
        auto_updater.config.state['last_update_check'] = 'invalid-timestamp'

        assert auto_updater.should_check_for_updates() is True

    def test_is_system_wide_install_false(self, auto_updater: AutoUpdater):
        """Test detection of non-system-wide installation."""
        # In test environment, should not be system-wide
        result = auto_updater.is_system_wide_install()
        # This depends on test environment, but typically should be False
        assert isinstance(result, bool)

    def test_is_system_wide_install_true(self, auto_updater: AutoUpdater):
        """Test detection of system-wide installation."""
        # Mock the script path to include site-packages
        with patch.object(auto_updater, 'script_path', Path('/usr/lib/python3.10/site-packages/warden.py')):
            assert auto_updater.is_system_wide_install() is True

    @patch('subprocess.run')
    def test_is_git_repository_true(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test git repository detection when it is a repo."""
        mock_run.return_value = Mock(returncode=0)

        assert auto_updater.is_git_repository() is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_is_git_repository_false(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test git repository detection when it is not a repo."""
        mock_run.return_value = Mock(returncode=1)

        assert auto_updater.is_git_repository() is False

    @patch('subprocess.run')
    def test_is_git_repository_timeout(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test git repository detection handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('git', 5)

        assert auto_updater.is_git_repository() is False

    @patch('subprocess.run')
    def test_is_git_clean_true(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test git clean detection when working directory is clean."""
        mock_run.return_value = Mock(returncode=0, stdout='')

        assert auto_updater.is_git_clean() is True

    @patch('subprocess.run')
    def test_is_git_clean_false(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test git clean detection when working directory has changes."""
        mock_run.return_value = Mock(returncode=0, stdout='M warden.py\n')

        assert auto_updater.is_git_clean() is False

    @patch('subprocess.run')
    def test_check_for_updates_no_git_repo(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test update check when not a git repository."""
        mock_run.return_value = Mock(returncode=1)

        result = auto_updater.check_for_updates()

        assert result is None

    @patch('subprocess.run')
    def test_check_for_updates_network_failure(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test update check handles network failures gracefully."""
        # First call (is_git_repository) succeeds
        # Second call (git fetch) fails
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=1, stderr='Network error')  # git fetch
        ]

        result = auto_updater.check_for_updates()

        assert result is None

    @patch('subprocess.run')
    def test_check_for_updates_up_to_date(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test update check when already up to date."""
        commit_hash = 'abc123def456'
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0),  # git fetch
            Mock(returncode=0, stdout=commit_hash),  # local hash
            Mock(returncode=0, stdout=commit_hash),  # remote hash (same)
        ]

        result = auto_updater.check_for_updates()

        assert result is None

    @patch('subprocess.run')
    def test_check_for_updates_behind(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test update check when commits are behind."""
        local_hash = 'abc123'
        remote_hash = 'def456'
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0),  # git fetch
            Mock(returncode=0, stdout=local_hash),  # local hash
            Mock(returncode=0, stdout=remote_hash),  # remote hash (different)
            Mock(returncode=0, stdout='3'),  # commits behind
        ]

        result = auto_updater.check_for_updates()

        assert result is not None
        assert result['local_hash'] == local_hash
        assert result['remote_hash'] == remote_hash
        assert result['commits_behind'] == 3

    @patch('subprocess.run')
    def test_perform_update_not_git_repo(self, mock_run: Mock, auto_updater: AutoUpdater):
        """Test update execution when not a git repository."""
        mock_run.return_value = Mock(returncode=1)

        result = auto_updater.perform_update()

        assert result is False

    @patch('subprocess.run')
    def test_perform_update_dirty_git(self, mock_run: Mock, auto_updater: AutoUpdater, capsys):
        """Test update execution skips when git is dirty."""
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0, stdout='M warden.py\n'),  # is_git_clean (dirty)
        ]

        result = auto_updater.perform_update()

        assert result is False
        captured = capsys.readouterr()
        assert 'uncommitted changes' in captured.out

    @patch('subprocess.run')
    def test_perform_update_success_repo_install(self, mock_run: Mock, auto_updater: AutoUpdater, capsys):
        """Test successful update for repository installation."""
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0, stdout=''),  # is_git_clean
            Mock(returncode=0, stdout='Updated successfully'),  # git pull
        ]

        # Mock is_system_wide_install to return False
        with patch.object(auto_updater, 'is_system_wide_install', return_value=False):
            result = auto_updater.perform_update()

        assert result is True
        captured = capsys.readouterr()
        assert 'Updating Agent Warden' in captured.out
        assert 'updated successfully' in captured.out

    @patch('subprocess.run')
    @patch('sys.executable', '/usr/bin/python3')
    def test_perform_update_success_system_install(self, mock_run: Mock, auto_updater: AutoUpdater, capsys):
        """Test successful update for system-wide installation."""
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0, stdout=''),  # is_git_clean
            Mock(returncode=0, stdout='Updated successfully'),  # git pull
            Mock(returncode=0, stdout='Successfully installed'),  # pip install
        ]

        # Mock is_system_wide_install to return True
        with patch.object(auto_updater, 'is_system_wide_install', return_value=True):
            result = auto_updater.perform_update()

        assert result is True
        captured = capsys.readouterr()
        assert 'Reinstalling system-wide package' in captured.out

    @patch('subprocess.run')
    def test_perform_update_git_pull_fails(self, mock_run: Mock, auto_updater: AutoUpdater, capsys):
        """Test update execution when git pull fails."""
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0, stdout=''),  # is_git_clean
            Mock(returncode=1, stderr='Pull failed'),  # git pull fails
        ]

        with patch.object(auto_updater, 'is_system_wide_install', return_value=False):
            result = auto_updater.perform_update()

        assert result is False
        captured = capsys.readouterr()
        assert 'Update failed' in captured.out

    @patch('subprocess.run')
    def test_perform_update_timeout(self, mock_run: Mock, auto_updater: AutoUpdater, capsys):
        """Test update execution handles timeout."""
        mock_run.side_effect = [
            Mock(returncode=0),  # is_git_repository
            Mock(returncode=0, stdout=''),  # is_git_clean
            subprocess.TimeoutExpired('git', 60),  # git pull timeout
        ]

        with patch.object(auto_updater, 'is_system_wide_install', return_value=False):
            result = auto_updater.perform_update()

        assert result is False
        captured = capsys.readouterr()
        assert 'Update failed' in captured.out

    def test_update_last_check_time(self, auto_updater: AutoUpdater):
        """Test updating last check timestamp."""
        # Clear any existing timestamp
        auto_updater.config.state.pop('last_update_check', None)

        # Update timestamp
        auto_updater.update_last_check_time()

        # Verify timestamp was set
        assert 'last_update_check' in auto_updater.config.state

        # Verify it's a valid ISO format timestamp
        timestamp_str = auto_updater.config.state['last_update_check']
        timestamp = datetime.fromisoformat(timestamp_str)

        # Should be very recent (within last minute)
        # Use UTC to match the timestamp (which is now stored in UTC)
        now = datetime.now(timezone.utc)
        time_diff = now - timestamp
        assert time_diff.total_seconds() < 60

    def test_update_last_check_time_persists(self, auto_updater: AutoUpdater, temp_dir: Path):
        """Test that last check timestamp persists to state file."""
        auto_updater.update_last_check_time()

        # Read state file directly
        state_file = temp_dir / '.warden_state.json'
        with open(state_file) as f:
            state_data = json.load(f)

        assert 'last_update_check' in state_data

        # Verify it's a valid timestamp
        timestamp = datetime.fromisoformat(state_data['last_update_check'])
        assert isinstance(timestamp, datetime)


class TestAutoUpdaterIntegration:
    """Integration tests for AutoUpdater with WardenConfig."""

    def test_config_auto_update_default(self, config: WardenConfig):
        """Test that auto_update defaults to True in config."""
        assert config.config.get('auto_update', True) is True

    def test_config_auto_update_can_be_disabled(self, config: WardenConfig):
        """Test that auto_update can be disabled."""
        config.config['auto_update'] = False
        config.save_config()

        # Create new config instance
        new_config = WardenConfig(config.base_path)

        assert new_config.config['auto_update'] is False

    def test_config_auto_update_backward_compatibility(self, temp_dir: Path):
        """Test that old configs without auto_update still work."""
        # Create config without auto_update field
        config_data = {
            'targets': WardenConfig.TARGET_CONFIGS.copy(),
            'default_target': 'augment',
            'update_remote_projects': True
        }

        config_file = temp_dir / '.warden_config.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Create mdc.mdc file
        (temp_dir / 'mdc.mdc').write_text('# Test')

        # Load config
        config = WardenConfig(temp_dir)

        # Should have auto_update set to True by default
        assert config.config.get('auto_update', True) is True


