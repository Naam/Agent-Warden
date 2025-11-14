"""Tests for GitHubPackage class."""

from datetime import datetime

import pytest

from warden import GitHubPackage


class TestGitHubPackage:
    """Test cases for GitHubPackage."""

    def test_init_basic(self):
        """Test basic initialization."""
        package = GitHubPackage("owner", "repo")

        assert package.owner == "owner"
        assert package.repo == "repo"
        assert package.ref == "main"
        assert package.name == "owner/repo"
        assert package.directory_name == "owner-repo"
        assert package.github_url == "https://github.com/owner/repo.git"

    def test_init_with_ref(self):
        """Test initialization with specific ref."""
        package = GitHubPackage("owner", "repo", "v1.0.0")

        assert package.ref == "v1.0.0"

    def test_init_with_installed_info(self):
        """Test initialization with installed information."""
        installed_at = datetime.now().isoformat()
        package = GitHubPackage(
            "owner", "repo", "main",
            installed_ref="abc123",
            installed_at=installed_at
        )

        assert package.installed_ref == "abc123"
        assert package.installed_at == installed_at

    def test_to_dict(self):
        """Test conversion to dictionary."""
        package = GitHubPackage("owner", "repo", "v1.0.0")
        package.installed_ref = "abc123"

        data = package.to_dict()

        assert data['owner'] == "owner"
        assert data['repo'] == "repo"
        assert data['ref'] == "v1.0.0"
        assert data['installed_ref'] == "abc123"
        assert 'installed_at' in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'owner': 'testowner',
            'repo': 'testrepo',
            'ref': 'v2.0.0',
            'installed_ref': 'def456',
            'installed_at': '2024-01-01T00:00:00'
        }

        package = GitHubPackage.from_dict(data)

        assert package.owner == 'testowner'
        assert package.repo == 'testrepo'
        assert package.ref == 'v2.0.0'
        assert package.installed_ref == 'def456'
        assert package.installed_at == '2024-01-01T00:00:00'

    def test_from_spec_basic(self):
        """Test creation from spec string."""
        package = GitHubPackage.from_spec("owner/repo")

        assert package.owner == "owner"
        assert package.repo == "repo"
        assert package.ref == "main"

    def test_from_spec_with_ref(self):
        """Test creation from spec string with ref."""
        package = GitHubPackage.from_spec("owner/repo@v1.0.0")

        assert package.owner == "owner"
        assert package.repo == "repo"
        assert package.ref == "v1.0.0"

    def test_from_spec_invalid(self):
        """Test creation from invalid spec string."""
        with pytest.raises(ValueError, match="Invalid package spec"):
            GitHubPackage.from_spec("invalid-spec")

    def test_directory_name_special_chars(self):
        """Test directory name with special characters."""
        package = GitHubPackage("owner-name", "repo.name")

        assert package.directory_name == "owner-name-repo.name"

    def test_github_url_format(self):
        """Test GitHub URL format."""
        package = GitHubPackage("owner", "repo")

        assert package.github_url == "https://github.com/owner/repo.git"
