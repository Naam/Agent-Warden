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

    def test_find_project_case_insensitive_exact_match(self, manager: WardenManager, sample_project_dir: Path):
        """Test case-insensitive project lookup with exact match."""
        # Install a project
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule'])
        project_name = project_state.name

        # Exact match should work
        result = manager._find_project_case_insensitive(project_name)
        assert result == project_name

    def test_find_project_case_insensitive_different_case(self, manager: WardenManager, sample_project_dir: Path):
        """Test case-insensitive project lookup with different casing."""
        # Install a project
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule'])
        project_name = project_state.name

        # Different cases should all find the project
        assert manager._find_project_case_insensitive(project_name.upper()) == project_name
        assert manager._find_project_case_insensitive(project_name.title()) == project_name
        assert manager._find_project_case_insensitive(project_name.swapcase()) == project_name

    def test_find_project_case_insensitive_not_found(self, manager: WardenManager):
        """Test case-insensitive project lookup when project doesn't exist."""
        result = manager._find_project_case_insensitive('nonexistent')
        assert result is None

    def test_update_project_case_insensitive(self, manager: WardenManager, sample_project_dir: Path):
        """Test that update_project works with case-insensitive project names."""
        # Install a project
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule'])
        project_name = project_state.name

        # Update with different casing should work
        result = manager.update_project(project_name.upper())
        assert result.name == project_name

    def test_add_to_project_case_insensitive(self, manager: WardenManager, sample_project_dir: Path):
        """Test that add_to_project works with case-insensitive project names."""
        # Install a project with one rule
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule'])
        project_name = project_state.name

        # Add another rule with different casing
        result = manager.add_to_project(project_name.upper(), rule_names=['rule1'])
        assert result.name == project_name
        assert len(result.targets['augment']['installed_rules']) == 2

    def test_remove_from_project_case_insensitive(self, manager: WardenManager, sample_project_dir: Path):
        """Test that remove_from_project works with case-insensitive project names."""
        # Install a project with rules
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule', 'rule1'])
        project_name = project_state.name

        # Remove with different casing should work
        result = manager.remove_from_project(project_name.title(), rule_names=['test-rule'], skip_confirm=True)
        assert 'test-rule' in result['removed_rules']

    def test_rename_project_case_insensitive_old_name(self, manager: WardenManager, sample_project_dir: Path):
        """Test that rename_project finds old name case-insensitively but preserves new name casing."""
        # Install a project
        project_state = manager.install_project(str(sample_project_dir), target='augment', rule_names=['test-rule'])
        project_name = project_state.name

        # Rename with different casing for old name
        result = manager.rename_project(project_name.upper(), 'MyNewProject')
        assert result.name == 'MyNewProject'

        # Old name should be gone, new name should exist with exact casing
        assert project_name not in manager.config.state['projects']
        assert 'MyNewProject' in manager.config.state['projects']
        assert 'mynewproject' not in manager.config.state['projects']
