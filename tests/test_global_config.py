"""Tests for global configuration installation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from warden import WardenError, WardenManager


class TestGlobalConfigInstallation:
    """Test cases for global configuration installation."""

    def test_install_global_config_claude_new_file(self, manager: WardenManager, tmp_path: Path):
        """Test installing Claude global config when file does not exist."""
        # Mock the global config path to use tmp_path
        claude_dir = tmp_path / '.claude'
        claude_config = claude_dir / 'CLAUDE.md'

        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            result = manager.install_global_config('claude', force=False)

            assert result is True
            assert claude_config.exists()

            # Verify content structure
            content = claude_config.read_text()
            assert '# Claude Code CLI Global Instructions' in content
            assert '# BEGIN AGENT WARDEN MANAGED SECTION' in content
            assert '# END AGENT WARDEN MANAGED SECTION' in content
            assert '@' in content  # Include directive

            # Verify warden-rules.md was created
            warden_rules = claude_dir / 'warden-rules.md'
            assert warden_rules.exists()
            rules_content = warden_rules.read_text()
            assert '# Agent Warden Rules' in rules_content

    def test_install_global_config_claude_existing_file_no_section(self, manager: WardenManager, tmp_path: Path):
        """Test installing Claude global config when file exists without managed section."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        claude_config = claude_dir / 'CLAUDE.md'

        # Create existing file with custom content
        existing_content = """# My Custom Instructions

These are my personal instructions.
Do not modify this content.
"""
        claude_config.write_text(existing_content)

        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            result = manager.install_global_config('claude', force=True)

            assert result is True

            # Verify custom content is preserved
            new_content = claude_config.read_text()
            assert 'My Custom Instructions' in new_content
            assert 'my personal instructions' in new_content

            # Verify managed section was added
            assert '# BEGIN AGENT WARDEN MANAGED SECTION' in new_content
            assert '# END AGENT WARDEN MANAGED SECTION' in new_content

    def test_install_global_config_claude_existing_file_with_section(self, manager: WardenManager, tmp_path: Path):
        """Test installing Claude global config when file exists with managed section."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        claude_config = claude_dir / 'CLAUDE.md'

        # Create existing file with managed section
        existing_content = """# My Custom Instructions

# BEGIN AGENT WARDEN MANAGED SECTION
@/old/path/to/rules.md
# END AGENT WARDEN MANAGED SECTION

More custom content.
"""
        claude_config.write_text(existing_content)

        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            result = manager.install_global_config('claude', force=True)

            assert result is True

            # Verify custom content is preserved
            new_content = claude_config.read_text()
            assert 'My Custom Instructions' in new_content
            assert 'More custom content' in new_content

            # Verify managed section was updated (not duplicated)
            assert new_content.count('# BEGIN AGENT WARDEN MANAGED SECTION') == 1
            assert new_content.count('# END AGENT WARDEN MANAGED SECTION') == 1

            # Verify old path was replaced
            assert '/old/path/to/rules.md' not in new_content

    def test_install_global_config_windsurf(self, manager: WardenManager, tmp_path: Path):
        """Test installing Windsurf global config."""
        windsurf_dir = tmp_path / '.codeium' / 'windsurf' / 'memories'
        windsurf_config = windsurf_dir / 'global_rules.md'

        with patch.object(manager.config, 'get_global_config_path', return_value=windsurf_config):
            result = manager.install_global_config('windsurf', force=False)

            assert result is True
            assert windsurf_config.exists()

            # Verify content structure
            content = windsurf_config.read_text()
            assert '# Global Agent Warden Rules for Windsurf' in content
            assert 'global rules' in content.lower()

    def test_install_global_config_codex(self, manager: WardenManager, tmp_path: Path):
        """Test installing Codex global config."""
        codex_dir = tmp_path / '.codex'
        codex_config = codex_dir / 'config.toml'

        with patch.object(manager.config, 'get_global_config_path', return_value=codex_config):
            result = manager.install_global_config('codex', force=False)

            assert result is True
            assert codex_config.exists()

            # Verify TOML content structure
            content = codex_config.read_text()
            assert '[warden]' in content
            assert 'rules_dir' in content
            assert '[warden.targets]' in content
            assert 'default = "augment"' in content

    def test_install_global_config_unsupported_target(self, manager: WardenManager):
        """Test installing global config for target without global config support."""
        with pytest.raises(WardenError, match="does not support global configuration"):
            manager.install_global_config('cursor', force=False)

    def test_install_global_config_file_exists_no_force(self, manager: WardenManager, tmp_path: Path):
        """Test that installation fails when file exists and force is False."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        claude_config = claude_dir / 'CLAUDE.md'
        claude_config.write_text("Existing content")

        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            with pytest.raises(WardenError, match="Global config already exists.*Use --force"):
                manager.install_global_config('claude', force=False)

    def test_install_global_config_unknown_target(self, manager: WardenManager, tmp_path: Path):
        """Test installing global config for unknown target."""
        unknown_config = tmp_path / 'unknown.conf'

        with patch.object(manager.config, 'get_global_config_path', return_value=unknown_config):
            with pytest.raises(WardenError, match="Global config generation not implemented"):
                manager.install_global_config('unknown', force=False)

