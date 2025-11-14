"""Tests for GitHub package management functionality."""

from pathlib import Path
from unittest.mock import patch

import pytest

from warden import WardenError, WardenManager


class TestPackageManagement:
    """Test cases for GitHub package management."""

    @patch('warden.WardenManager._run_git_command')
    def test_install_package_success(self, mock_git, manager: WardenManager, temp_dir: Path):
        """Test successful package installation."""
        # Mock git commands
        mock_git.side_effect = [
            (0, "", ""),  # submodule add
            (0, "abc123", ""),  # rev-parse HEAD
        ]

        # Create mock package directory structure
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)
        rules_dir = package_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.mdc").write_text("# Test rule")

        package = manager.install_package("testuser/testrepo")

        assert package.owner == "testuser"
        assert package.repo == "testrepo"
        assert package.installed_ref == "abc123"
        assert "testuser/testrepo" in manager.config.registry['packages']

    @patch('warden.WardenManager._run_git_command')
    def test_install_package_with_ref(self, mock_git, manager: WardenManager):
        """Test package installation with specific ref."""
        mock_git.side_effect = [
            (0, "", ""),  # submodule add
            (0, "def456", ""),  # rev-parse HEAD
        ]

        # Create mock package directory
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)

        package = manager.install_package("testuser/testrepo@v1.0.0")

        assert package.ref == "v1.0.0"
        mock_git.assert_any_call([
            'submodule', 'add', '-b', 'v1.0.0',
            'https://github.com/testuser/testrepo.git',
            str(package_dir)
        ], cwd=manager.config.base_path)

    @patch('warden.WardenManager._run_git_command')
    def test_install_package_git_failure(self, mock_git, manager: WardenManager):
        """Test package installation with git failure."""
        mock_git.return_value = (1, "", "Git error")

        with pytest.raises(WardenError, match="Failed to clone repository"):
            manager.install_package("testuser/testrepo")

    def test_install_package_already_exists(self, manager: WardenManager):
        """Test installing package that already exists."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main'
        }

        # Create package directory
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)

        with pytest.raises(WardenError, match="already installed"):
            manager.install_package("testuser/testrepo")

    def test_install_package_invalid_spec(self, manager: WardenManager):
        """Test installing package with invalid spec."""
        with pytest.raises(WardenError, match="Invalid package spec"):
            manager.install_package("invalid-spec")

    @patch('warden.WardenManager._run_git_command')
    def test_update_package_success(self, mock_git, manager: WardenManager):
        """Test successful package update."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }

        # Create package directory
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)

        mock_git.side_effect = [
            (0, "", ""),  # fetch
            (0, "", ""),  # checkout
            (0, "", ""),  # pull
            (0, "def456", ""),  # rev-parse HEAD
        ]

        package = manager.update_package("testuser/testrepo")

        assert package.installed_ref == "def456"

    def test_update_package_not_found(self, manager: WardenManager):
        """Test updating non-existent package."""
        with pytest.raises(WardenError, match="not found"):
            manager.update_package("nonexistent/package")

    def test_remove_package_success(self, manager: WardenManager):
        """Test successful package removal."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main'
        }

        # Create package directory
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)
        (package_dir / "test.txt").write_text("test")

        result = manager.remove_package("testuser/testrepo")

        assert result is True
        assert not package_dir.exists()
        assert "testuser/testrepo" not in manager.config.registry['packages']

    def test_remove_package_not_found(self, manager: WardenManager):
        """Test removing non-existent package."""
        result = manager.remove_package("nonexistent/package")

        assert result is False

    def test_list_packages(self, manager: WardenManager):
        """Test listing packages."""
        # Add packages to registry
        manager.config.registry['packages']['user1/repo1'] = {
            'owner': 'user1',
            'repo': 'repo1',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }
        manager.config.registry['packages']['user2/repo2'] = {
            'owner': 'user2',
            'repo': 'repo2',
            'ref': 'v1.0.0',
            'installed_ref': 'def456',
            'installed_at': '2024-01-02T00:00:00'
        }

        packages = manager.list_packages()

        assert len(packages) == 2
        assert any(p.name == "user1/repo1" for p in packages)
        assert any(p.name == "user2/repo2" for p in packages)

    @patch('warden.WardenManager._run_git_command')
    def test_check_package_updates(self, mock_git, manager: WardenManager):
        """Test checking for package updates."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }

        # Create package directory
        package_dir = manager.config.packages_path / "testuser-testrepo"
        package_dir.mkdir(parents=True)

        mock_git.side_effect = [
            (0, "", ""),  # fetch
            (0, "def456", ""),  # rev-parse origin/main
            (0, "5", ""),  # rev-list --count
        ]

        updates = manager.check_package_updates()

        assert "testuser/testrepo" in updates
        assert updates["testuser/testrepo"]["current"] == "abc123"[:8]
        assert updates["testuser/testrepo"]["latest"] == "def456"[:8]
        assert updates["testuser/testrepo"]["commits_behind"] == 5
