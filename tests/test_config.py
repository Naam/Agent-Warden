"""Tests for WardenConfig class."""

from pathlib import Path

from warden import WardenConfig


class TestWardenConfig:
    """Test cases for WardenConfig."""

    def test_init_creates_directories(self, temp_dir: Path):
        """Test that initialization creates required directories."""
        config = WardenConfig(temp_dir)

        assert config.commands_path.exists()
        assert config.packages_path.exists()
        assert config.base_path.resolve() == temp_dir.resolve()

    def test_default_configuration(self, config: WardenConfig):
        """Test default configuration values."""
        assert config.config['default_target'] == 'augment'
        assert 'cursor' in config.config['targets']
        assert 'augment' in config.config['targets']
        assert 'claude' in config.config['targets']

    def test_get_target_config(self, config: WardenConfig):
        """Test getting target configuration."""
        cursor_config = config.get_target_config('cursor')
        assert cursor_config['rules_path'] == '.cursor/rules/'
        assert cursor_config['supports_commands'] is False

        augment_config = config.get_target_config('augment')
        assert augment_config['rules_path'] == '.augment/rules/'
        assert augment_config['commands_path'] == '.augment/commands/'
        assert augment_config['supports_commands'] is True

    def test_target_supports_commands(self, config: WardenConfig):
        """Test checking if target supports commands."""
        assert config.target_supports_commands('augment') is True
        assert config.target_supports_commands('claude') is True
        assert config.target_supports_commands('cursor') is False

    def test_get_available_targets(self, config: WardenConfig):
        """Test getting list of available targets."""
        targets = config.get_available_targets()
        assert 'cursor' in targets
        assert 'augment' in targets
        assert 'claude' in targets
        assert 'windsurf' in targets
        assert 'codex' in targets

    def test_save_and_load_config(self, config: WardenConfig):
        """Test saving and loading configuration."""
        # Modify config
        config.add_target('custom', '.custom/rules/')

        # Create new config instance
        new_config = WardenConfig(config.base_path)

        # Check that custom target was persisted
        assert 'custom' in new_config.get_available_targets()
        assert new_config.get_target_config('custom') == '.custom/rules/'

    def test_registry_operations(self, config: WardenConfig):
        """Test registry save and load operations."""
        # Add test data to registry
        config.registry['packages']['test/repo'] = {
            'owner': 'test',
            'repo': 'repo',
            'ref': 'main',
            'installed_ref': 'abc123',
            'installed_at': '2024-01-01T00:00:00'
        }

        config.save_registry()

        # Create new config and verify data persisted
        new_config = WardenConfig(config.base_path)
        assert 'test/repo' in new_config.registry['packages']
        assert new_config.registry['packages']['test/repo']['owner'] == 'test'

    def test_get_global_config_path(self, config: WardenConfig):
        """Test getting global configuration paths."""
        # Test Claude path (should exist)
        claude_path = config.get_global_config_path('claude')
        assert claude_path is not None
        assert 'CLAUDE.md' in str(claude_path)

        # Test Windsurf path
        windsurf_path = config.get_global_config_path('windsurf')
        assert windsurf_path is not None
        assert 'global_rules.md' in str(windsurf_path)

        # Test target without global config
        cursor_path = config.get_global_config_path('cursor')
        assert cursor_path is None

    def test_invalid_target(self, config: WardenConfig):
        """Test handling of invalid target - returns default target."""
        # get_target_config returns default target for unknown targets
        target_config = config.get_target_config('invalid_target')
        assert target_config == config.get_target_config('augment')

    def test_add_target(self, config: WardenConfig):
        """Test adding a new target."""
        # Add target to config manually
        config.config['targets']['newtarget'] = {
            'rules_path': '.newtarget/rules/',
            'commands_path': '.newtarget/commands/',
            'supports_commands': True
        }

        target_config = config.get_target_config('newtarget')
        assert target_config['rules_path'] == '.newtarget/rules/'
        assert target_config['commands_path'] == '.newtarget/commands/'
        assert target_config['supports_commands'] is True
