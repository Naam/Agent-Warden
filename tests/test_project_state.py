"""Tests for ProjectState class."""

from datetime import datetime
from pathlib import Path

from warden import ProjectState, WardenConfig


class TestProjectState:
    """Test cases for ProjectState."""

    def test_init_basic(self, temp_dir: Path):
        """Test basic initialization."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path))

        # Add a target
        state.add_target("augment", "symlink", has_rules=True, has_commands=False)

        assert state.name == "test_project"
        assert state.path == project_path.resolve()
        assert state.has_target("augment")
        assert state.targets['augment']['has_rules'] is True
        assert state.targets['augment']['has_commands'] is False
        assert state.targets['augment']['install_type'] == "symlink"

    def test_init_with_options(self, temp_dir: Path):
        """Test initialization with options."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path))

        # Add a target with commands
        state.add_target("cursor", "copy", has_rules=False, has_commands=True,
                        installed_commands=["cmd1", "cmd2"])

        assert state.has_target("cursor")
        assert state.targets['cursor']['has_rules'] is False
        assert state.targets['cursor']['has_commands'] is True
        assert state.targets['cursor']['install_type'] == "copy"
        assert len(state.targets['cursor']['installed_commands']) == 2
        assert state.targets['cursor']['installed_commands'][0]['name'] == "cmd1"
        assert state.targets['cursor']['installed_commands'][1]['name'] == "cmd2"

    def test_to_dict(self, temp_dir: Path):
        """Test conversion to dictionary."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path))
        state.add_target("augment", "symlink", installed_commands=["cmd1"])

        data = state.to_dict()

        assert data['name'] == "test_project"
        assert data['path'] == str(project_path.resolve())
        # New format uses 'targets' instead of flat structure
        assert 'targets' in data
        assert 'augment' in data['targets']
        assert data['targets']['augment']['install_type'] == "symlink"
        assert 'timestamp' in data

    def test_from_dict(self):
        """Test creation from dictionary (old format conversion)."""
        data = {
            'name': 'test_project',
            'path': '/path/to/project',
            'target': 'claude',
            'has_rules': False,
            'has_commands': True,
            'install_type': 'copy',
            'installed_commands': ['cmd1', 'cmd2'],
            'timestamp': '2024-01-01T00:00:00'
        }

        state = ProjectState.from_dict(data)

        assert state.name == 'test_project'
        assert str(state.path) == str(Path('/path/to/project').resolve())
        # Old format should be converted to new format
        assert state.has_target('claude')
        assert state.targets['claude']['has_rules'] is False
        assert state.targets['claude']['has_commands'] is True
        assert state.targets['claude']['install_type'] == 'copy'
        assert len(state.targets['claude']['installed_commands']) == 2
        assert state.targets['claude']['installed_commands'][0]['name'] == 'cmd1'
        assert state.targets['claude']['installed_commands'][1]['name'] == 'cmd2'

    def test_get_rules_destination_path(self, config: WardenConfig, temp_dir: Path):
        """Test getting rules destination path."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path))
        state.add_target("augment", "symlink")

        rules_path = state.get_rules_destination_path(config, "augment")
        expected = project_path.resolve() / ".augment" / "rules" / "mdc.mdc"

        assert rules_path == expected

    def test_get_commands_destination_path(self, config: WardenConfig, temp_dir: Path):
        """Test getting commands destination path."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path))
        state.add_target("augment", "symlink")

        commands_path = state.get_commands_destination_path(config, "augment")
        expected = project_path.resolve() / ".augment" / "commands"

        assert commands_path == expected

    def test_update_timestamp(self, temp_dir: Path):
        """Test updating timestamp."""
        project_path = temp_dir / "test_project"
        state = ProjectState("test_project", str(project_path), "augment", "symlink")

        original_timestamp = state.timestamp
        import time
        time.sleep(0.01)  # Ensure time difference
        state.timestamp = datetime.now().isoformat()

        assert state.timestamp != original_timestamp
