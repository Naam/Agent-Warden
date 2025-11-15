"""Tests for fs_backend error handling paths."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from fs_backend import (
    BackendError,
    LocalBackend,
    RemoteBackend,
    RemoteOperationError,
    RemotePermissionError,
    SSHConnectionError,
)


class TestRemoteBackendErrorHandling:
    """Test error handling in RemoteBackend."""

    def test_ssh_connection_refused(self):
        """Test SSH connection refused error."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 255
            mock_result.stderr = 'Connection refused'
            mock_result.stdout = ''
            mock_run.return_value = mock_result

            with pytest.raises(SSHConnectionError, match="Cannot connect"):
                backend._run_ssh_command('test')

    def test_ssh_connection_timeout(self):
        """Test SSH connection timeout error."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 255
            mock_result.stderr = 'Connection timed out'
            mock_result.stdout = ''
            mock_run.return_value = mock_result

            with pytest.raises(SSHConnectionError, match="Cannot connect"):
                backend._run_ssh_command('test')

    def test_ssh_permission_denied(self):
        """Test SSH permission denied error."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 255
            mock_result.stderr = 'Permission denied'
            mock_result.stdout = ''
            mock_run.return_value = mock_result

            with pytest.raises(RemotePermissionError, match="Permission denied"):
                backend._run_ssh_command('test')

    def test_ssh_generic_error(self):
        """Test generic SSH error."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Some other error'
            mock_result.stdout = ''
            mock_run.return_value = mock_result

            with pytest.raises(RemoteOperationError, match="SSH command failed"):
                backend._run_ssh_command('test')

    def test_ssh_timeout_expired(self):
        """Test SSH timeout expired exception."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('ssh', 30)

            with pytest.raises(SSHConnectionError, match="timed out"):
                backend._run_ssh_command('test')

    def test_ssh_client_not_found(self):
        """Test SSH client not found error."""
        backend = RemoteBackend('user@host')

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(BackendError, match="SSH client not found"):
                backend._run_ssh_command('test')

    def test_remote_path_resolution_with_base_path(self):
        """Test remote path resolution with base path."""
        backend = RemoteBackend('host', user='user', path='/home/user')

        # Relative path should be joined with base_path
        resolved = backend._resolve_remote_path('project/file.txt')
        assert resolved == '/home/user/project/file.txt'

        # Absolute path should remain unchanged
        resolved = backend._resolve_remote_path('/absolute/path')
        assert resolved == '/absolute/path'

    def test_remote_path_resolution_without_base_path(self):
        """Test remote path resolution without base path."""
        backend = RemoteBackend('host', user='user')

        # Path should remain unchanged
        resolved = backend._resolve_remote_path('project/file.txt')
        assert resolved == 'project/file.txt'

    def test_supports_symlinks_returns_false(self):
        """Test that remote backend does not support symlinks."""
        backend = RemoteBackend('host', user='user')
        assert backend.supports_symlinks() is False

    def test_get_location_string_with_base_path(self):
        """Test location string with base path."""
        backend = RemoteBackend('host', user='user', path='/home/user')
        location = backend.get_location_string()
        assert location == 'user@host:/home/user'

    def test_get_location_string_without_base_path(self):
        """Test location string without base path."""
        backend = RemoteBackend('host', user='user')
        location = backend.get_location_string()
        assert location == 'user@host'


class TestLocalBackendErrorHandling:
    """Test error handling in LocalBackend."""

    def test_copy_file_source_not_exists(self, tmp_path: Path):
        """Test copying nonexistent source file."""
        backend = LocalBackend()

        source = tmp_path / 'nonexistent.txt'
        dest = tmp_path / 'dest.txt'

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            backend.copy_file(str(source), str(dest))

    def test_checksum_not_exists(self, tmp_path: Path):
        """Test getting checksum of nonexistent file."""
        backend = LocalBackend()

        nonexistent = tmp_path / 'nonexistent.txt'

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            backend.checksum(str(nonexistent))

    def test_supports_symlinks_returns_true(self):
        """Test that local backend supports symlinks."""
        backend = LocalBackend()
        assert backend.supports_symlinks() is True

    def test_get_location_string_returns_local(self):
        """Test location string for local backend."""
        backend = LocalBackend()
        location = backend.get_location_string()
        assert location == 'local'

