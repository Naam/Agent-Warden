#!/usr/bin/env python3
"""
Filesystem backend abstraction layer.

Provides unified interface for both local and remote (SSH) file system operations.
This module encapsulates all filesystem interactions, allowing Agent Warden to work
seamlessly with both local paths and remote SSH locations.
"""

import hashlib
import os
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple


class BackendError(Exception):
    """Base exception for backend errors."""
    pass


class RemoteOperationError(BackendError):
    """Base class for remote operation errors."""
    pass


class SSHConnectionError(RemoteOperationError):
    """SSH connection failed."""
    pass


class RemotePermissionError(RemoteOperationError):
    """Permission denied on remote."""
    pass


class RemotePathError(RemoteOperationError):
    """Remote path doesn't exist or invalid."""
    pass


class FileSystemBackend(ABC):
    """Abstract base class for file system operations."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        pass

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        pass

    @abstractmethod
    def mkdir(self, path: str, parents: bool = True, exist_ok: bool = True):
        """Create directory."""
        pass

    @abstractmethod
    def copy_file(self, source: str, dest: str):
        """Copy file from source to dest."""
        pass

    @abstractmethod
    def remove_file(self, path: str):
        """Remove a file."""
        pass

    @abstractmethod
    def checksum(self, path: str) -> str:
        """Calculate SHA256 checksum of file."""
        pass

    @abstractmethod
    def supports_symlinks(self) -> bool:
        """Return whether this backend supports symlinks."""
        pass

    def create_symlink(self, source: str, dest: str):
        """Create a symlink. May raise NotImplementedError."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support symlinks")

    @abstractmethod
    def get_location_string(self) -> str:
        """Get string representation of this location."""
        pass


class LocalBackend(FileSystemBackend):
    """Backend for local file system operations."""

    def __init__(self, base_path: Optional[str] = None):
        """Initialize local backend.

        Args:
            base_path: Optional base path for relative operations
        """
        self.base_path = Path(base_path).resolve() if base_path else None

    def _resolve_path(self, path: str) -> Path:
        """Resolve path to absolute Path object."""
        p = Path(path)
        if self.base_path and not p.is_absolute():
            return self.base_path / p
        return p.resolve() if p.is_absolute() else Path.cwd() / p

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        return self._resolve_path(path).exists()

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        return self._resolve_path(path).is_dir()

    def mkdir(self, path: str, parents: bool = True, exist_ok: bool = True):
        """Create directory."""
        self._resolve_path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def copy_file(self, source: str, dest: str):
        """Copy file from source to dest."""
        src_path = self._resolve_path(source)
        dest_path = self._resolve_path(dest)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing file if it exists
        if dest_path.exists():
            dest_path.unlink()

        shutil.copy2(src_path, dest_path)

    def remove_file(self, path: str):
        """Remove a file."""
        p = self._resolve_path(path)
        if p.exists() or p.is_symlink():
            p.unlink()

    def checksum(self, path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        file_path = self._resolve_path(path)
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def supports_symlinks(self) -> bool:
        """Return whether this backend supports symlinks."""
        return True

    def create_symlink(self, source: str, dest: str):
        """Create a symlink from source to dest."""
        src_path = self._resolve_path(source)
        dest_path = self._resolve_path(dest)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing file/symlink if it exists
        if dest_path.exists() or dest_path.is_symlink():
            dest_path.unlink()

        dest_path.symlink_to(src_path)

    def get_location_string(self) -> str:
        """Get string representation of this location."""
        return str(self.base_path) if self.base_path else "local"


class RemoteBackend(FileSystemBackend):
    """Backend for SSH remote file system operations."""

    def __init__(self, host: str, user: Optional[str] = None, path: Optional[str] = None):
        """Initialize remote backend.

        Args:
            host: SSH host (can be alias from ~/.ssh/config)
            user: SSH user (optional, can be in host or SSH config)
            path: Base path on remote system
        """
        self.host = host
        self.user = user
        self.base_path = path
        self.ssh_target = f"{user}@{host}" if user else host
        self.transfer_tool = self._detect_transfer_tool()

    def _detect_transfer_tool(self) -> str:
        """Detect available transfer tool (rsync preferred)."""
        if shutil.which('rsync'):
            return 'rsync'
        return 'scp'

    def _run_ssh_command(self, command: str, check: bool = True) -> Tuple[int, str, str]:
        """Execute command on remote via SSH.

        Args:
            command: Command to execute
            check: Whether to raise exception on non-zero exit

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        ssh_cmd = ['ssh', self.ssh_target, command]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if check and result.returncode != 0:
                # Check for common SSH errors
                stderr_lower = result.stderr.lower()
                if 'connection refused' in stderr_lower or 'connection timed out' in stderr_lower:
                    raise SSHConnectionError(f"Cannot connect to {self.ssh_target}: {result.stderr}")
                elif 'permission denied' in stderr_lower:
                    raise RemotePermissionError(f"Permission denied on {self.ssh_target}: {result.stderr}")
                else:
                    raise RemoteOperationError(f"SSH command failed: {result.stderr}")

            return result.returncode, result.stdout.strip(), result.stderr.strip()

        except subprocess.TimeoutExpired:
            raise SSHConnectionError(f"SSH connection to {self.ssh_target} timed out") from None
        except FileNotFoundError:
            raise BackendError("SSH client not found. Please install OpenSSH.") from None

    def _resolve_remote_path(self, path: str) -> str:
        """Resolve path on remote system."""
        # Treat paths starting with ~ or / as absolute (shell will expand ~)
        if self.base_path and not (path.startswith('/') or path.startswith('~')):
            # Relative path - join with base_path
            return f"{self.base_path.rstrip('/')}/{path}"
        return path

    def _get_remote_location(self, path: str) -> str:
        """Get full remote location string for scp/rsync."""
        remote_path = self._resolve_remote_path(path)
        return f"{self.ssh_target}:{remote_path}"

    def _quote_remote_path(self, path: str) -> str:
        """Quote a remote path for use in SSH commands, handling ~ expansion."""
        # If path starts with ~, use $HOME instead so shell can expand it
        if path.startswith('~/'):
            # Replace ~ with $HOME and quote the rest
            return f'"$HOME/{path[2:]}"'
        elif path == '~':
            return '"$HOME"'
        else:
            # Regular path - use single quotes
            return f"'{path}'"

    def exists(self, path: str) -> bool:
        """Check if path exists on remote."""
        remote_path = self._resolve_remote_path(path)
        quoted_path = self._quote_remote_path(remote_path)
        code, _, _ = self._run_ssh_command(f"test -e {quoted_path}", check=False)
        return code == 0

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory on remote."""
        remote_path = self._resolve_remote_path(path)
        quoted_path = self._quote_remote_path(remote_path)
        code, _, _ = self._run_ssh_command(f"test -d {quoted_path}", check=False)
        return code == 0

    def mkdir(self, path: str, parents: bool = True, exist_ok: bool = True):
        """Create directory on remote."""
        remote_path = self._resolve_remote_path(path)

        if exist_ok and self.exists(remote_path):
            return

        quoted_path = self._quote_remote_path(remote_path)
        mkdir_cmd = f"mkdir {'-p ' if parents else ''}{quoted_path}"
        self._run_ssh_command(mkdir_cmd)

    def copy_file(self, source: str, dest: str):
        """Copy file to remote destination.

        Args:
            source: Local source file path
            dest: Remote destination path (relative to base_path)
        """
        # Source is always local (from warden installation)
        # Dest is remote path

        # Ensure destination directory exists on remote
        dest_remote = self._resolve_remote_path(dest)
        dest_dir = os.path.dirname(dest_remote)
        if dest_dir:
            self.mkdir(dest_dir, parents=True, exist_ok=True)

        # Remove existing file if it exists
        if self.exists(dest):
            self.remove_file(dest)

        # Transfer file
        remote_dest = self._get_remote_location(dest)

        if self.transfer_tool == 'rsync':
            cmd = ['rsync', '-az', '--checksum', source, remote_dest]
        else:  # scp
            cmd = ['scp', '-q', source, remote_dest]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RemoteOperationError(f"File transfer failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise RemoteOperationError(f"File transfer to {self.ssh_target} timed out") from None
        except FileNotFoundError:
            raise BackendError(f"{self.transfer_tool} not found. Please install it.") from None

    def remove_file(self, path: str):
        """Remove a file on remote."""
        remote_path = self._resolve_remote_path(path)
        quoted_path = self._quote_remote_path(remote_path)
        self._run_ssh_command(f"rm -f {quoted_path}")

    def checksum(self, path: str) -> str:
        """Calculate SHA256 checksum of remote file."""
        remote_path = self._resolve_remote_path(path)
        quoted_path = self._quote_remote_path(remote_path)

        # Try sha256sum first (Linux), then shasum (macOS)
        code, stdout, _ = self._run_ssh_command(
            f"sha256sum {quoted_path} 2>/dev/null || shasum -a 256 {quoted_path}",
            check=False
        )

        if code != 0:
            raise RemotePathError(f"Cannot calculate checksum for {remote_path}")

        # Extract checksum from output (first field)
        return stdout.split()[0]

    def supports_symlinks(self) -> bool:
        """Remote backend does not support symlinks."""
        return False

    def get_location_string(self) -> str:
        """Get string representation of this location."""
        if self.base_path:
            return f"{self.ssh_target}:{self.base_path}"
        return self.ssh_target


def parse_location(location: str) -> Tuple[str, FileSystemBackend]:
    """Parse location string and return (path, backend).

    Args:
        location: Location string, either:
            - Local path: "/path/to/dir" or "~/path" or "relative/path"
            - Remote SSH: "[user@]host:path"

    Returns:
        Tuple of (path, backend_instance)

    Examples:
        "/local/path" -> ("/local/path", LocalBackend())
        "user@server:/remote/path" -> ("/remote/path", RemoteBackend("server", "user", "/remote/path"))
        "server:/path" -> ("/path", RemoteBackend("server", None, "/path"))
    """
    # Regex to match SSH format: [user@]host:path
    # Must have colon, and host part cannot be a Windows drive letter
    ssh_pattern = r'^(?:([^@]+)@)?([^:]+):(.+)$'
    match = re.match(ssh_pattern, location)

    if match and not _is_windows_path(location):
        # Remote SSH location
        user, host, path = match.groups()
        return path, RemoteBackend(host=host, user=user, path=path)
    else:
        # Local path
        return location, LocalBackend()


def _is_windows_path(path: str) -> bool:
    """Check if path looks like a Windows path (e.g., C:/...)."""
    return bool(re.match(r'^[A-Za-z]:', path))

