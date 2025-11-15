"""Tests for WardenManager core functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from warden import WardenManager


class TestWardenManagerCore:
    """Test cases for WardenManager core functionality."""

    def test_init(self, manager: WardenManager):
        """Test manager initialization."""
        assert manager.config is not None
        assert manager.config.commands_path.exists()
        assert manager.config.packages_path.exists()

    def test_get_available_commands(self, manager: WardenManager):
        """Test getting available commands."""
        commands = manager._get_available_commands()

        assert "test-command" in commands
        assert isinstance(commands, list)

    def test_discover_package_content(self, manager: WardenManager, mock_git_repo: Path):
        """Test discovering package content."""
        content = manager._discover_package_content(mock_git_repo)

        assert "typescript" in content['rules']
        assert "react" in content['rules']
        assert "deploy" in content['commands']

    def test_discover_package_content_no_directories(self, manager: WardenManager, temp_dir: Path):
        """Test discovering content when no rules/commands directories exist."""
        empty_repo = temp_dir / "empty_repo"
        empty_repo.mkdir()

        content = manager._discover_package_content(empty_repo)

        assert content['rules'] == []
        assert content['commands'] == []

    def test_discover_package_content_filters_meta_rules(self, manager: WardenManager, temp_dir: Path):
        """Test that meta-rules are filtered out during discovery."""
        repo_dir = temp_dir / "test_repo"
        rules_dir = repo_dir / "rules"
        rules_dir.mkdir(parents=True)

        # Create meta-rules that should be filtered
        (rules_dir / "mdc.mdc").write_text("# Meta rule")
        (rules_dir / "meta.mdc").write_text("# Meta rule")
        (rules_dir / "format.mdc").write_text("# Format rule")
        (rules_dir / "template.md").write_text("---\ndescription: Template\n---\n# Template rule")

        # Create actual rules that should be included
        (rules_dir / "python.md").write_text("---\ndescription: Python\n---\n# Python rule")
        (rules_dir / "javascript.md").write_text("---\ndescription: JavaScript\n---\n# JavaScript rule")

        content = manager._discover_package_content(repo_dir)

        assert "python" in content['rules']
        assert "javascript" in content['rules']
        assert "mdc" not in content['rules']
        assert "meta" not in content['rules']
        assert "format" not in content['rules']
        assert "template" not in content['rules']

    def test_resolve_command_path_builtin(self, manager: WardenManager):
        """Test resolving built-in command path."""
        path, source = manager._resolve_command_path("test-command")

        assert path.name == "test-command.md"
        assert source == "built-in"

    def test_resolve_command_path_package(self, manager: WardenManager, mock_git_repo: Path):
        """Test resolving package command path."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }

        path, source = manager._resolve_command_path("testuser/testrepo:deploy")

        assert path.name == "deploy.md"
        assert source == "package:testuser/testrepo"

    def test_resolve_command_path_not_found(self, manager: WardenManager):
        """Test resolving non-existent command path."""
        with pytest.raises(FileNotFoundError):
            manager._resolve_command_path("nonexistent-command")

    def test_resolve_rule_path_package(self, manager: WardenManager, mock_git_repo: Path):
        """Test resolving package rule path."""
        # Add package to registry
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }

        path, source = manager._resolve_rule_path("testuser/testrepo:typescript")

        assert path.name == "typescript.md"
        assert source == "package:testuser/testrepo"

    def test_resolve_rule_path_builtin_not_allowed(self, manager: WardenManager):
        """Test that built-in rules are not allowed for installation."""
        with pytest.raises(FileNotFoundError, match="No built-in rules available"):
            manager._resolve_rule_path("mdc")

    def test_search_packages(self, manager: WardenManager, mock_git_repo: Path):
        """Test searching packages."""
        # Add package to registry with content
        manager.config.registry['packages']['testuser/testrepo'] = {
            'owner': 'testuser',
            'repo': 'testrepo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00',
            'content': {
                'rules': ['typescript', 'react'],
                'commands': ['deploy', 'test']
            }
        }

        results = manager.search_packages("type")

        assert "testuser/testrepo:typescript" in results['rules']
        assert len(results['commands']) == 0  # No commands match "type"

    @patch('warden.subprocess.run')
    def test_run_git_command_success(self, mock_run, manager: WardenManager):
        """Test successful git command execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        code, stdout, stderr = manager._run_git_command(['status'])

        assert code == 0
        assert stdout == "success output"
        assert stderr == ""

    @patch('warden.subprocess.run')
    def test_run_git_command_failure(self, mock_run, manager: WardenManager):
        """Test failed git command execution."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_run.return_value = mock_result

        code, stdout, stderr = manager._run_git_command(['invalid'])

        assert code == 1
        assert stdout == ""
        assert stderr == "error message"
