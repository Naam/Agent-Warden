"""
Tests for error handling paths in warden.py.

Targets uncovered error handling lines:
- Lines 91, 199, 216, 227: JSON/config loading errors
- Lines 237, 245, 253: Config/state/registry save errors
- Lines 365: Invalid package spec
- Lines 563, 680, 693, 705, 714, 725: FileNotFoundError paths
- Lines 575-576, 581, 584, 586-591: Location validation errors
- Lines 615-616: Permission errors
- Lines 1018, 1026, 1045-1047, 1096: WardenError paths
"""

from unittest.mock import mock_open, patch

import pytest

from warden import (
    GitHubPackage,
    InvalidTargetError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WardenError,
    WardenManager,
)


class TestConfigLoadingErrors:
    """Test error handling in config/state/registry loading."""

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    @patch('pathlib.Path.exists', return_value=True)
    def test_config_load_oserror(self, mock_exists, mock_file):
        """Test handling of OSError when loading config."""
        with patch('builtins.print') as mock_print:
            WardenManager()
            # Should print warning but not crash
            assert any('Warning' in str(call) for call in mock_print.call_args_list)

    @patch('builtins.open', mock_open(read_data='invalid json{'))
    @patch('pathlib.Path.exists', return_value=True)
    def test_config_load_json_decode_error(self, mock_exists):
        """Test handling of JSONDecodeError when loading config."""
        with patch('builtins.print') as mock_print:
            WardenManager()
            # Should print warning but not crash
            assert any('Warning' in str(call) for call in mock_print.call_args_list)


class TestConfigSavingErrors:
    """Test error handling in config/state/registry saving."""

    def test_save_config_oserror(self, tmp_path):
        """Test handling of OSError when saving config."""
        # Create required rules directory
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.md").write_text("---\ndescription: Test\n---\n# Test rules")

        manager = WardenManager(base_path=tmp_path)

        # Make config path read-only
        manager.config.config_path.touch()
        manager.config.config_path.chmod(0o444)

        with pytest.raises(RuntimeError, match="Could not save config file"):
            manager.config.save_config()

    def test_save_state_oserror(self, tmp_path):
        """Test handling of OSError when saving state."""
        # Create required rules directory
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "test.md").write_text("---\ndescription: Test\n---\n# Test rules")

        manager = WardenManager(base_path=tmp_path)

        # Make state path read-only
        manager.config.state_path.touch()
        manager.config.state_path.chmod(0o444)

        with pytest.raises(RuntimeError, match="Could not save state file"):
            manager.config.save_state()


class TestPackageSpecValidation:
    """Test package specification validation."""

    def test_invalid_package_spec_no_slash(self):
        """Test that invalid package spec (no slash) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid package spec"):
            GitHubPackage.from_spec("invalid-spec")


class TestProjectNotFoundErrors:
    """Test ProjectNotFoundError handling."""

    def test_update_project_not_found(self, manager):
        """Test updating non-existent project raises ProjectNotFoundError."""
        with pytest.raises(ProjectNotFoundError, match="not found"):
            manager.update_project("nonexistent-project")

    def test_sever_project_not_found(self, manager):
        """Test severing non-existent project raises ProjectNotFoundError."""
        with pytest.raises(ProjectNotFoundError, match="not found"):
            manager.sever_project("nonexistent-project")

    def test_rename_project_not_found(self, manager):
        """Test renaming non-existent project raises ProjectNotFoundError."""
        with pytest.raises(ProjectNotFoundError, match="not found"):
            manager.rename_project("nonexistent", "new-name")


class TestInvalidTargetErrors:
    """Test InvalidTargetError handling."""

    def test_install_with_invalid_target(self, manager, temp_dir):
        """Test installing with invalid target raises InvalidTargetError."""
        project_path = temp_dir / "test-project"
        project_path.mkdir()

        with pytest.raises(InvalidTargetError, match="Unknown target"):
            manager.install_project(project_path, target="invalid-target")


class TestWardenErrors:
    """Test WardenError handling."""

    def test_empty_custom_project_name(self, manager, temp_dir):
        """Test that empty custom project name raises WardenError."""
        project_path = temp_dir / "test-project"
        project_path.mkdir()

        with pytest.raises(WardenError, match="cannot be empty"):
            manager.install_project(project_path, custom_name="   ")

    def test_rename_project_empty_name(self, manager, temp_dir):
        """Test that renaming to empty name raises WardenError."""
        # Create a project first
        project_path = temp_dir / "test-project"
        project_path.mkdir()
        manager.install_project(project_path)

        with pytest.raises(WardenError, match="cannot be empty"):
            manager.rename_project("test-project", "   ")

    def test_rename_project_already_exists(self, manager, temp_dir):
        """Test that renaming to existing name raises ProjectAlreadyExistsError."""
        # Create two projects
        project1 = temp_dir / "project1"
        project1.mkdir()
        manager.install_project(project1)

        project2 = temp_dir / "project2"
        project2.mkdir()
        manager.install_project(project2)

        with pytest.raises(ProjectAlreadyExistsError, match="already exists"):
            manager.rename_project("project1", "project2")


class TestFileNotFoundErrors:
    """Test FileNotFoundError handling."""

    def test_package_not_found_in_registry(self, manager):
        """Test that accessing non-existent package raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            manager._resolve_command_path("nonexistent-package:command")


class TestLocationValidationErrors:
    """Test location validation error handling."""

    def test_nonexistent_project_path(self, manager, temp_dir):
        """Test that non-existent project path raises WardenError."""
        nonexistent = temp_dir / "nonexistent"

        with pytest.raises(WardenError, match="does not exist"):
            manager.install_project(nonexistent)

    def test_project_path_is_file_not_directory(self, manager, temp_dir):
        """Test that file path (not directory) raises WardenError."""
        file_path = temp_dir / "file.txt"
        file_path.touch()

        with pytest.raises(WardenError, match="not a directory"):
            manager.install_project(file_path)

