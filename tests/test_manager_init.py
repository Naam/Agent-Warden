"""
Tests for WardenManager initialization and path resolution.

These tests ensure that WardenManager correctly resolves paths when
initialized with and without explicit base_path.
"""

from pathlib import Path

import pytest

from agent_warden.manager import WardenManager


class TestManagerInitialization:
    """Test WardenManager initialization and path resolution."""

    def test_manager_with_explicit_base_path(self, tmp_path: Path):
        """Test WardenManager with explicit base_path."""
        # Create required directories
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "test-rule.md").write_text("# Test Rule")

        # Initialize with explicit base_path
        manager = WardenManager(base_path=tmp_path)

        # Verify paths are correct
        assert manager.config.base_path == tmp_path
        assert manager.config.rules_dir == rules_dir
        assert manager.config.rules_dir.exists()

    def test_manager_default_base_path_resolution(self):
        """Test that WardenManager without base_path resolves to repo root.

        This test ensures that when WardenManager is in agent_warden/manager.py,
        it correctly resolves the base_path to the repository root (where warden.py
        and rules/ directory are located), not to the agent_warden/ directory.
        """
        # Initialize without base_path (uses default)
        manager = WardenManager()

        # The base_path should be the repository root
        # (where warden.py, rules/, commands/, etc. are located)
        expected_base = Path(__file__).parent.parent.resolve()

        assert manager.config.base_path == expected_base
        assert manager.config.rules_dir == expected_base / "rules"
        assert manager.config.rules_dir.exists(), \
            f"Rules directory not found at {manager.config.rules_dir}"

    def test_manager_rules_directory_must_exist(self, tmp_path: Path):
        """Test that WardenManager raises error if rules directory doesn't exist."""
        # Don't create rules directory
        with pytest.raises(FileNotFoundError, match="Rules directory not found"):
            WardenManager(base_path=tmp_path)

    def test_manager_config_paths(self, tmp_path: Path):
        """Test that all config paths are correctly set relative to base_path."""
        # Create required directories
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "test-rule.md").write_text("# Test Rule")

        manager = WardenManager(base_path=tmp_path)

        # Verify all paths are relative to base_path
        assert manager.config.config_path == tmp_path / ".warden_config.json"
        assert manager.config.state_path == tmp_path / ".warden_state.json"
        assert manager.config.rules_dir == tmp_path / "rules"
        assert manager.config.commands_path == tmp_path / "commands"
        assert manager.config.packages_path == tmp_path / "packages"
        assert manager.config.registry_path == tmp_path / "packages" / ".registry.json"

