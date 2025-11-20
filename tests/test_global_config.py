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

    def test_install_global_config_cursor(self, manager: WardenManager, tmp_path: Path):
        """Test installing Cursor global config."""
        cursor_rules_dir = tmp_path / '.cursor' / 'rules'

        # Create some test rules in the warden rules directory
        manager.config.rules_dir.mkdir(parents=True, exist_ok=True)
        test_rule1 = manager.config.rules_dir / 'test-rule-1.md'
        test_rule1.write_text("""---
description: Test rule 1
---

# Test Rule 1
This is test rule 1.
""")
        test_rule2 = manager.config.rules_dir / 'test-rule-2.md'
        test_rule2.write_text("""---
description: Test rule 2
---

# Test Rule 2
This is test rule 2.
""")

        with patch.object(manager.config, 'get_global_config_path', return_value=cursor_rules_dir):
            result = manager.install_global_config('cursor', force=False)

            assert result is True
            assert cursor_rules_dir.exists()
            assert cursor_rules_dir.is_dir()

            # Verify rule files were copied
            assert (cursor_rules_dir / 'test-rule-1.md').exists()
            assert (cursor_rules_dir / 'test-rule-2.md').exists()

            # Verify content
            content1 = (cursor_rules_dir / 'test-rule-1.md').read_text()
            assert 'Test Rule 1' in content1

            content2 = (cursor_rules_dir / 'test-rule-2.md').read_text()
            assert 'Test Rule 2' in content2

    def test_install_global_config_cursor_force_overwrite(self, manager: WardenManager, tmp_path: Path):
        """Test that cursor global config can be overwritten with --force."""
        cursor_rules_dir = tmp_path / '.cursor' / 'rules'
        cursor_rules_dir.mkdir(parents=True)

        # Create existing rule file
        existing_rule = cursor_rules_dir / 'old-rule.md'
        existing_rule.write_text("Old content")

        # Create new rules in warden
        manager.config.rules_dir.mkdir(parents=True, exist_ok=True)
        new_rule = manager.config.rules_dir / 'new-rule.md'
        new_rule.write_text("""---
description: New rule
---

# New Rule
This is a new rule.
""")

        with patch.object(manager.config, 'get_global_config_path', return_value=cursor_rules_dir):
            result = manager.install_global_config('cursor', force=True)

            assert result is True
            # Old rule should still exist (we don't delete, just add/update)
            assert existing_rule.exists()
            # New rule should be added
            assert (cursor_rules_dir / 'new-rule.md').exists()

    def test_install_global_config_unsupported_target(self, manager: WardenManager):
        """Test installing global config for target without global config support."""
        with pytest.raises(WardenError, match="does not support global configuration"):
            manager.install_global_config('augment', force=False)

    def test_install_global_config_file_exists_no_force(self, manager: WardenManager, tmp_path: Path):
        """Test that installation fails when file exists and force is False."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True)
        claude_config = claude_dir / 'CLAUDE.md'
        claude_config.write_text("Existing content")

        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            with pytest.raises(WardenError, match="Global config already exists.*Use --force"):
                manager.install_global_config('claude', force=False)

    def test_global_install_creates_global_project(self, manager: WardenManager, tmp_path: Path):
        """Test that global-install creates a @global project entry in state."""
        cursor_rules_dir = tmp_path / '.cursor' / 'rules'

        # Create test rules
        manager.config.rules_dir.mkdir(parents=True, exist_ok=True)
        test_rule = manager.config.rules_dir / 'test-rule.md'
        test_rule.write_text("""---
description: Test rule
---

# Test Rule
""")

        with patch.object(manager.config, 'get_global_config_path', return_value=cursor_rules_dir):
            # Install global config for cursor
            manager.install_global_config('cursor', force=False, rule_names=['test-rule'])

            # Verify @global project was created
            assert '@global' in manager.config.state['projects']

            global_project_data = manager.config.state['projects']['@global']
            assert global_project_data['name'] == '@global'
            # Path will be resolved, just check it contains @global
            assert '@global' in global_project_data['path']

            # Verify cursor target was added
            assert 'targets' in global_project_data
            assert 'cursor' in global_project_data['targets']

            cursor_target = global_project_data['targets']['cursor']
            assert cursor_target['install_type'] == 'copy'
            assert len(cursor_target['installed_rules']) == 1
            assert cursor_target['installed_rules'][0]['name'] == 'test-rule'

    def test_global_install_updates_existing_global_project(self, manager: WardenManager, tmp_path: Path):
        """Test that subsequent global-install updates the @global project."""
        cursor_rules_dir = tmp_path / '.cursor' / 'rules'
        claude_dir = tmp_path / '.claude'
        claude_config = claude_dir / 'CLAUDE.md'

        # Create test rules
        manager.config.rules_dir.mkdir(parents=True, exist_ok=True)
        rule1 = manager.config.rules_dir / 'rule1.md'
        rule1.write_text("# Rule 1")
        rule2 = manager.config.rules_dir / 'rule2.md'
        rule2.write_text("# Rule 2")

        # Install cursor first
        with patch.object(manager.config, 'get_global_config_path', return_value=cursor_rules_dir):
            manager.install_global_config('cursor', force=False, rule_names=['rule1'])

        # Install claude second
        with patch.object(manager.config, 'get_global_config_path', return_value=claude_config):
            manager.install_global_config('claude', force=False, rule_names=['rule2'])

        # Verify @global project has both targets
        assert '@global' in manager.config.state['projects']
        global_project_data = manager.config.state['projects']['@global']

        assert 'cursor' in global_project_data['targets']
        assert 'claude' in global_project_data['targets']

        # Verify each target has its rules
        assert global_project_data['targets']['cursor']['installed_rules'][0]['name'] == 'rule1'
        assert global_project_data['targets']['claude']['installed_rules'][0]['name'] == 'rule2'

    def test_install_global_config_unknown_target(self, manager: WardenManager, tmp_path: Path):
        """Test installing global config for unknown target."""
        unknown_config = tmp_path / 'unknown.conf'

        with patch.object(manager.config, 'get_global_config_path', return_value=unknown_config):
            with pytest.raises(WardenError, match="Global config generation not implemented"):
                manager.install_global_config('unknown', force=False)

