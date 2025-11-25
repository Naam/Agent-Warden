#!/usr/bin/env python3
"""Tests for filesystem backend abstraction layer."""

import hashlib
from unittest.mock import Mock, patch

import pytest

from fs_backend import (
    LocalBackend,
    RemoteBackend,
    RemotePermissionError,
    SSHConnectionError,
    parse_location,
)


class TestLocalBackend:
    """Tests for LocalBackend."""

    def test_init_with_base_path(self, tmp_path):
        """Test initialization with base path."""
        backend = LocalBackend(str(tmp_path))
        assert backend.base_path == tmp_path

    def test_init_without_base_path(self):
        """Test initialization without base path."""
        backend = LocalBackend()
        assert backend.base_path is None

    def test_exists_true(self, tmp_path):
        """Test exists returns True for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        backend = LocalBackend(str(tmp_path))
        assert backend.exists("test.txt") is True

    def test_exists_false(self, tmp_path):
        """Test exists returns False for non-existing file."""
        backend = LocalBackend(str(tmp_path))
        assert backend.exists("nonexistent.txt") is False

    def test_is_dir_true(self, tmp_path):
        """Test is_dir returns True for directory."""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        backend = LocalBackend(str(tmp_path))
        assert backend.is_dir("testdir") is True

    def test_is_dir_false(self, tmp_path):
        """Test is_dir returns False for file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        backend = LocalBackend(str(tmp_path))
        assert backend.is_dir("test.txt") is False

    def test_mkdir(self, tmp_path):
        """Test directory creation."""
        backend = LocalBackend(str(tmp_path))
        backend.mkdir("newdir/subdir")

        assert (tmp_path / "newdir" / "subdir").is_dir()

    def test_copy_file(self, tmp_path):
        """Test file copying."""
        source = tmp_path / "source.txt"
        source.write_text("test content")

        backend = LocalBackend(str(tmp_path))
        backend.copy_file(str(source), "dest.txt")

        dest = tmp_path / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_copy_file_creates_parent_dirs(self, tmp_path):
        """Test copy_file creates parent directories."""
        source = tmp_path / "source.txt"
        source.write_text("test content")

        backend = LocalBackend(str(tmp_path))
        backend.copy_file(str(source), "subdir/dest.txt")

        dest = tmp_path / "subdir" / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_copy_file_overwrites_existing(self, tmp_path):
        """Test copy_file overwrites existing file."""
        source = tmp_path / "source.txt"
        source.write_text("new content")

        dest = tmp_path / "dest.txt"
        dest.write_text("old content")

        backend = LocalBackend(str(tmp_path))
        backend.copy_file(str(source), "dest.txt")

        assert dest.read_text() == "new content"

    def test_remove_file(self, tmp_path):
        """Test file removal."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        backend = LocalBackend(str(tmp_path))
        backend.remove_file("test.txt")

        assert not test_file.exists()

    def test_checksum(self, tmp_path):
        """Test checksum calculation."""
        test_file = tmp_path / "test.txt"
        content = "test content"
        test_file.write_text(content)

        # Calculate expected checksum
        expected = hashlib.sha256(content.encode()).hexdigest()

        backend = LocalBackend(str(tmp_path))
        assert backend.checksum("test.txt") == expected

    def test_supports_symlinks(self):
        """Test that local backend supports symlinks."""
        backend = LocalBackend()
        assert backend.supports_symlinks() is True

    def test_create_symlink(self, tmp_path):
        """Test symlink creation."""
        source = tmp_path / "source.txt"
        source.write_text("content")

        backend = LocalBackend(str(tmp_path))
        backend.create_symlink(str(source), "link.txt")

        link = tmp_path / "link.txt"
        assert link.is_symlink()
        assert link.resolve() == source

    def test_create_symlink_overwrites_existing(self, tmp_path):
        """Test create_symlink overwrites existing symlink."""
        source1 = tmp_path / "source1.txt"
        source1.write_text("content1")
        source2 = tmp_path / "source2.txt"
        source2.write_text("content2")

        backend = LocalBackend(str(tmp_path))
        backend.create_symlink(str(source1), "link.txt")
        backend.create_symlink(str(source2), "link.txt")

        link = tmp_path / "link.txt"
        assert link.resolve() == source2

    def test_get_location_string(self, tmp_path):
        """Test location string representation."""
        backend = LocalBackend(str(tmp_path))
        assert backend.get_location_string() == str(tmp_path)

    def test_copy_files_batch_empty(self, tmp_path):
        """Test copy_files_batch with empty list."""
        backend = LocalBackend(str(tmp_path))
        # Should not raise any errors
        backend.copy_files_batch([])

    def test_copy_files_batch_single_file(self, tmp_path):
        """Test copy_files_batch with single file."""
        source = tmp_path / "source.txt"
        source.write_text("test content")

        backend = LocalBackend(str(tmp_path))
        backend.copy_files_batch([
            (str(source), "dest.txt")
        ])

        dest = tmp_path / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_copy_files_batch_multiple_files(self, tmp_path):
        """Test copy_files_batch with multiple files."""
        source1 = tmp_path / "source1.txt"
        source1.write_text("content 1")
        source2 = tmp_path / "source2.txt"
        source2.write_text("content 2")
        source3 = tmp_path / "source3.txt"
        source3.write_text("content 3")

        backend = LocalBackend(str(tmp_path))
        backend.copy_files_batch([
            (str(source1), "dest1.txt"),
            (str(source2), "subdir/dest2.txt"),
            (str(source3), "subdir/dest3.txt"),
        ])

        assert (tmp_path / "dest1.txt").read_text() == "content 1"
        assert (tmp_path / "subdir" / "dest2.txt").read_text() == "content 2"
        assert (tmp_path / "subdir" / "dest3.txt").read_text() == "content 3"

    def test_copy_files_batch_creates_dirs(self, tmp_path):
        """Test copy_files_batch creates destination directories."""
        source = tmp_path / "source.txt"
        source.write_text("test content")

        backend = LocalBackend(str(tmp_path))
        backend.copy_files_batch([
            (str(source), "deep/nested/dir/dest.txt")
        ], create_dirs=True)

        dest = tmp_path / "deep" / "nested" / "dir" / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"


class TestRemoteBackend:
    """Tests for RemoteBackend."""

    def test_init_with_user(self):
        """Test initialization with user."""
        backend = RemoteBackend(host="server.com", user="testuser", path="/remote/path")
        assert backend.host == "server.com"
        assert backend.user == "testuser"
        assert backend.base_path == "/remote/path"
        assert backend.ssh_target == "testuser@server.com"

    def test_init_without_user(self):
        """Test initialization without user."""
        backend = RemoteBackend(host="server.com", path="/remote/path")
        assert backend.host == "server.com"
        assert backend.user is None
        assert backend.ssh_target == "server.com"

    def test_detect_transfer_tool_rsync(self):
        """Test transfer tool detection prefers rsync."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/rsync'
            backend = RemoteBackend(host="server.com")
            assert backend.transfer_tool == 'rsync'

    def test_detect_transfer_tool_scp_fallback(self):
        """Test transfer tool falls back to scp."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            backend = RemoteBackend(host="server.com")
            assert backend.transfer_tool == 'scp'

    @patch('subprocess.run')
    def test_run_ssh_command_success(self, mock_run):
        """Test successful SSH command execution."""
        mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")

        backend = RemoteBackend(host="server.com", user="testuser")
        code, stdout, stderr = backend._run_ssh_command("ls -la")

        assert code == 0
        assert stdout == "output"
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ['ssh', 'testuser@server.com', 'ls -la']

    @patch('subprocess.run')
    def test_run_ssh_command_connection_refused(self, mock_run):
        """Test SSH command with connection refused."""
        mock_run.return_value = Mock(
            returncode=255,
            stdout="",
            stderr="Connection refused"
        )

        backend = RemoteBackend(host="server.com")
        with pytest.raises(SSHConnectionError, match="Cannot connect"):
            backend._run_ssh_command("ls")

    @patch('subprocess.run')
    def test_run_ssh_command_permission_denied(self, mock_run):
        """Test SSH command with permission denied."""
        mock_run.return_value = Mock(
            returncode=255,
            stdout="",
            stderr="Permission denied (publickey)"
        )

        backend = RemoteBackend(host="server.com")
        with pytest.raises(RemotePermissionError, match="Permission denied"):
            backend._run_ssh_command("ls")

    @patch('subprocess.run')
    def test_run_ssh_command_timeout(self, mock_run):
        """Test SSH command timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired(cmd="ssh", timeout=30)

        backend = RemoteBackend(host="server.com")
        with pytest.raises(SSHConnectionError, match="timed out"):
            backend._run_ssh_command("ls")

    @patch('subprocess.run')
    def test_exists_true(self, mock_run):
        """Test exists returns True for existing remote file."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backend = RemoteBackend(host="server.com", path="/remote")
        assert backend.exists("test.txt") is True

        # Verify correct command
        assert mock_run.call_args[0][0] == ['ssh', 'server.com', "test -e '/remote/test.txt'"]

    @patch('subprocess.run')
    def test_exists_false(self, mock_run):
        """Test exists returns False for non-existing remote file."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        backend = RemoteBackend(host="server.com", path="/remote")
        assert backend.exists("test.txt") is False

    @patch('subprocess.run')
    def test_is_dir_true(self, mock_run):
        """Test is_dir returns True for remote directory."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backend = RemoteBackend(host="server.com", path="/remote")
        assert backend.is_dir("testdir") is True

        assert mock_run.call_args[0][0] == ['ssh', 'server.com', "test -d '/remote/testdir'"]

    @patch('subprocess.run')
    def test_is_dir_false(self, mock_run):
        """Test is_dir returns False for remote file."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

        backend = RemoteBackend(host="server.com", path="/remote")
        assert backend.is_dir("test.txt") is False

    @patch('subprocess.run')
    def test_mkdir(self, mock_run):
        """Test remote directory creation."""
        # First call checks if exists (returns 1 = doesn't exist)
        # Second call creates the directory
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr=""),  # exists check
            Mock(returncode=0, stdout="", stderr="")   # mkdir
        ]

        backend = RemoteBackend(host="server.com", path="/remote")
        backend.mkdir("newdir/subdir")

        # Check the mkdir call (second call)
        assert mock_run.call_args_list[1][0][0] == ['ssh', 'server.com', "mkdir -p '/remote/newdir/subdir'"]

    @patch('subprocess.run')
    def test_copy_file_with_rsync(self, mock_run):
        """Test file copy using rsync."""
        # Mock for mkdir, exists check, and rsync
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value='/usr/bin/rsync'):
            backend = RemoteBackend(host="server.com", user="testuser", path="/remote")
            backend.copy_file("/local/source.txt", "dest.txt")

        # Find the rsync call
        rsync_calls = [c for c in mock_run.call_args_list if 'rsync' in str(c)]
        assert len(rsync_calls) > 0
        rsync_call = rsync_calls[0][0][0]
        assert rsync_call[0] == 'rsync'
        assert '/local/source.txt' in rsync_call
        assert 'testuser@server.com:/remote/dest.txt' in rsync_call

    @patch('subprocess.run')
    def test_copy_file_with_scp(self, mock_run):
        """Test file copy using scp."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value=None):
            backend = RemoteBackend(host="server.com", path="/remote")
            backend.copy_file("/local/source.txt", "dest.txt")

        # Find the scp call
        scp_calls = [c for c in mock_run.call_args_list if 'scp' in str(c)]
        assert len(scp_calls) > 0
        scp_call = scp_calls[0][0][0]
        assert scp_call[0] == 'scp'
        assert '/local/source.txt' in scp_call
        assert 'server.com:/remote/dest.txt' in scp_call

    @patch('subprocess.run')
    def test_remove_file(self, mock_run):
        """Test remote file removal."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        backend = RemoteBackend(host="server.com", path="/remote")
        backend.remove_file("test.txt")

        assert mock_run.call_args[0][0] == ['ssh', 'server.com', "rm -f '/remote/test.txt'"]

    @patch('subprocess.run')
    def test_checksum(self, mock_run):
        """Test remote checksum calculation."""
        expected_checksum = "abc123def456"
        mock_run.return_value = Mock(
            returncode=0,
            stdout=f"{expected_checksum}  /remote/test.txt",
            stderr=""
        )

        backend = RemoteBackend(host="server.com", path="/remote")
        checksum = backend.checksum("test.txt")

        assert checksum == expected_checksum

    def test_supports_symlinks(self):
        """Test that remote backend does not support symlinks."""
        backend = RemoteBackend(host="server.com")
        assert backend.supports_symlinks() is False

    def test_create_symlink_raises(self):
        """Test that create_symlink raises NotImplementedError."""
        backend = RemoteBackend(host="server.com")
        with pytest.raises(NotImplementedError, match="does not support symlinks"):
            backend.create_symlink("/source", "/dest")

    def test_get_location_string(self):
        """Test location string representation."""
        backend = RemoteBackend(host="server.com", user="testuser", path="/remote/path")
        assert backend.get_location_string() == "testuser@server.com:/remote/path"

    @patch('subprocess.run')
    def test_copy_files_batch_empty(self, mock_run):
        """Test copy_files_batch with empty list."""
        backend = RemoteBackend(host="server.com", path="/remote")
        # Should not raise any errors and not make any calls
        backend.copy_files_batch([])
        assert mock_run.call_count == 0

    @patch('subprocess.run')
    def test_copy_files_batch_single_file_rsync(self, mock_run):
        """Test copy_files_batch with single file using rsync."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value='/usr/bin/rsync'):
            backend = RemoteBackend(host="server.com", user="testuser", path="/remote")
            backend.copy_files_batch([
                ("/local/file1.txt", "dest1.txt")
            ])

        # Should have 2 calls: mkdir and rsync
        assert mock_run.call_count == 2

        # Check mkdir call
        mkdir_call = mock_run.call_args_list[0][0][0]
        assert mkdir_call[0] == 'ssh'
        assert 'mkdir -p' in mkdir_call[2]

        # Check rsync call
        rsync_call = mock_run.call_args_list[1][0][0]
        assert rsync_call[0] == 'rsync'
        assert '/local/file1.txt' in rsync_call
        assert 'testuser@server.com:/remote/' in rsync_call[-1]

    @patch('subprocess.run')
    def test_copy_files_batch_multiple_files_same_dir(self, mock_run):
        """Test copy_files_batch with multiple files to same directory."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value='/usr/bin/rsync'):
            backend = RemoteBackend(host="server.com", path="/remote")
            backend.copy_files_batch([
                ("/local/file1.txt", "rules/file1.txt"),
                ("/local/file2.txt", "rules/file2.txt"),
                ("/local/file3.txt", "rules/file3.txt"),
            ])

        # Should have 2 calls: mkdir and rsync (all files in one rsync call)
        assert mock_run.call_count == 2

        # Check rsync call has all 3 files
        rsync_call = mock_run.call_args_list[1][0][0]
        assert rsync_call[0] == 'rsync'
        assert '/local/file1.txt' in rsync_call
        assert '/local/file2.txt' in rsync_call
        assert '/local/file3.txt' in rsync_call

    @patch('subprocess.run')
    def test_copy_files_batch_multiple_dirs(self, mock_run):
        """Test copy_files_batch with files to different directories."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value='/usr/bin/rsync'):
            backend = RemoteBackend(host="server.com", path="/remote")
            backend.copy_files_batch([
                ("/local/rule1.txt", "rules/rule1.txt"),
                ("/local/rule2.txt", "rules/rule2.txt"),
                ("/local/cmd1.txt", "commands/cmd1.txt"),
            ])

        # Should have 3 calls: mkdir (for both dirs), rsync (rules), rsync (commands)
        assert mock_run.call_count == 3

        # Check mkdir call creates both directories
        mkdir_call = mock_run.call_args_list[0][0][0]
        assert 'mkdir -p' in mkdir_call[2]
        # Should contain both directory paths
        assert 'rules' in mkdir_call[2] or 'commands' in mkdir_call[2]

    @patch('subprocess.run')
    def test_copy_files_batch_with_scp(self, mock_run):
        """Test copy_files_batch using scp when rsync not available."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value=None):  # No rsync
            backend = RemoteBackend(host="server.com", path="/remote")
            backend.copy_files_batch([
                ("/local/file1.txt", "dest/file1.txt"),
                ("/local/file2.txt", "dest/file2.txt"),
            ])

        # Should use scp instead of rsync
        scp_call = mock_run.call_args_list[1][0][0]
        assert scp_call[0] == 'scp'
        assert '/local/file1.txt' in scp_call
        assert '/local/file2.txt' in scp_call

    @patch('subprocess.run')
    def test_copy_files_batch_no_create_dirs(self, mock_run):
        """Test copy_files_batch with create_dirs=False."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch('shutil.which', return_value='/usr/bin/rsync'):
            backend = RemoteBackend(host="server.com", path="/remote")
            backend.copy_files_batch([
                ("/local/file1.txt", "dest/file1.txt")
            ], create_dirs=False)

        # Should only have rsync call, no mkdir
        assert mock_run.call_count == 1
        rsync_call = mock_run.call_args_list[0][0][0]
        assert rsync_call[0] == 'rsync'


class TestParseLocation:
    """Tests for parse_location function."""

    def test_parse_local_absolute_path(self):
        """Test parsing local absolute path."""
        path, backend = parse_location("/local/path/to/project")
        assert path == "/local/path/to/project"
        assert isinstance(backend, LocalBackend)

    def test_parse_local_relative_path(self):
        """Test parsing local relative path."""
        path, backend = parse_location("relative/path")
        assert path == "relative/path"
        assert isinstance(backend, LocalBackend)

    def test_parse_local_home_path(self):
        """Test parsing local home path."""
        path, backend = parse_location("~/projects/myapp")
        assert path == "~/projects/myapp"
        assert isinstance(backend, LocalBackend)

    def test_parse_remote_with_user(self):
        """Test parsing remote path with user."""
        path, backend = parse_location("user@server.com:/remote/path")
        assert path == "/remote/path"
        assert isinstance(backend, RemoteBackend)
        assert backend.host == "server.com"
        assert backend.user == "user"
        assert backend.base_path == "/remote/path"

    def test_parse_remote_without_user(self):
        """Test parsing remote path without user."""
        path, backend = parse_location("server.com:/remote/path")
        assert path == "/remote/path"
        assert isinstance(backend, RemoteBackend)
        assert backend.host == "server.com"
        assert backend.user is None

    def test_parse_remote_with_ssh_alias(self):
        """Test parsing remote with SSH config alias."""
        path, backend = parse_location("myserver:/var/www/app")
        assert path == "/var/www/app"
        assert isinstance(backend, RemoteBackend)
        assert backend.host == "myserver"

    def test_parse_windows_path_as_local(self):
        """Test that Windows paths are treated as local."""
        path, backend = parse_location("C:/Users/test/project")
        assert path == "C:/Users/test/project"
        assert isinstance(backend, LocalBackend)

    def test_parse_remote_relative_path(self):
        """Test parsing remote with relative path."""
        path, backend = parse_location("server:relative/path")
        assert path == "relative/path"
        assert isinstance(backend, RemoteBackend)

