"""Tests for CLI commands: project remove and project untrack."""

from pathlib import Path
from unittest.mock import patch

from warden import WardenManager


class TestCLIProjectRemove:
    """Test CLI for removing rules/commands from projects."""

    def test_cli_remove_with_rules(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project --rules rule1 rule2"""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1', 'test']
        )

        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'remove', project.name,
            '--rules', 'test-rule', 'rule1'
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.print') as mock_print:
                    result = main()

        assert result == 0

        # Verify output
        output = ' '.join([str(call[0][0]) for call in mock_print.call_args_list])
        assert 'SUCCESS' in output
        assert 'test-rule' in output
        assert 'rule1' in output

        # Verify rules removed
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert 'test-rule' not in installed_rules
        assert 'rule1' not in installed_rules
        assert 'test' in installed_rules

    def test_cli_remove_with_commands(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project --commands cmd1 cmd2"""
        # Install project with commands
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            install_commands=True,
            command_names=['test-command', 'test']
        )

        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'remove', project.name,
            '--commands', 'test-command'
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                result = main()

        assert result == 0

        # Verify command removed
        updated_project = manager.config.state['projects'][project.name]
        installed_commands = [c['name'] for c in updated_project['targets']['augment']['installed_commands']]
        assert 'test-command' not in installed_commands
        assert 'test' in installed_commands

    def test_cli_remove_with_both_rules_and_commands(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project --rules X --commands Y"""
        # Install project with both
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1'],
            install_commands=True,
            command_names=['test-command']
        )

        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'remove', project.name,
            '--rules', 'test-rule',
            '--commands', 'test-command'
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                result = main()

        assert result == 0

        # Verify both removed
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        installed_commands = [c['name'] for c in updated_project['targets']['augment']['installed_commands']]
        assert 'test-rule' not in installed_rules
        assert 'test-command' not in installed_commands

    def test_cli_remove_with_target(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project --rules X --target cursor"""
        # Install project with two targets
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        manager.install_project(
            sample_project_dir,
            target='cursor',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'remove', project.name,
            '--rules', 'test-rule',
            '--target', 'cursor'
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                result = main()

        assert result == 0

        # Verify removed from cursor only
        updated_project = manager.config.state['projects'][project.name]
        cursor_rules = [r['name'] for r in updated_project['targets']['cursor']['installed_rules']]
        augment_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert 'test-rule' not in cursor_rules
        assert 'test-rule' in augment_rules

    def test_cli_remove_without_flags_shows_error(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project (no flags = error)"""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Mock CLI args without --rules or --commands
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', 'project', 'remove', project.name
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.print') as mock_print:
                    result = main()

        assert result == 1

        # Verify error message
        output = ' '.join([str(call[0][0]) for call in mock_print.call_args_list])
        assert 'ERROR' in output
        assert 'Must specify --rules or --commands' in output
        assert 'untrack' in output  # Should suggest untrack command

    def test_cli_remove_with_yes_flag(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project remove my-project --rules X --yes"""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule', 'rule1']
        )

        # Mock CLI args with --yes
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'remove', project.name,
            '--rules', 'test-rule'
        ])

        # Run CLI (should not prompt) with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                result = main()

        assert result == 0

        # Verify rule removed
        updated_project = manager.config.state['projects'][project.name]
        installed_rules = [r['name'] for r in updated_project['targets']['augment']['installed_rules']]
        assert 'test-rule' not in installed_rules


class TestCLIProjectUntrack:
    """Test CLI for untracking projects."""

    def test_cli_untrack_command(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test: warden project untrack my-project"""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'untrack', project.name
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.print') as mock_print:
                    result = main()

        assert result == 0

        # Verify output
        output = ' '.join([str(call[0][0]) for call in mock_print.call_args_list])
        assert 'SUCCESS' in output
        assert 'Untracked' in output
        assert 'not deleted' in output

        # Verify project untracked
        assert project.name not in manager.config.state['projects']

        # Verify files still exist
        rule_file = sample_project_dir / ".augment" / "rules" / "test-rule.md"
        assert rule_file.exists()

    def test_cli_untrack_with_confirmation(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test untrack with confirmation prompt."""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Mock CLI args without --yes
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', 'project', 'untrack', project.name
        ])

        # Mock user confirming
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.input', return_value='y'):
                    result = main()

        assert result == 0

        # Verify project untracked
        assert project.name not in manager.config.state['projects']

    def test_cli_untrack_with_confirmation_declined(self, manager: WardenManager, sample_project_dir: Path, monkeypatch):
        """Test untrack with confirmation declined."""
        # Install project
        project = manager.install_project(
            sample_project_dir,
            target='augment',
            use_copy=True,
            rule_names=['test-rule']
        )

        # Mock CLI args without --yes
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', 'project', 'untrack', project.name
        ])

        # Mock user declining
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.input', return_value='n'):
                    with patch('builtins.print'):
                        result = main()

        # When user declines, untrack_project returns False, which CLI interprets as "not found"
        # This is a bit confusing but matches current behavior
        assert result == 1

        # Verify project NOT untracked
        assert project.name in manager.config.state['projects']

    def test_cli_untrack_nonexistent_project(self, manager: WardenManager, monkeypatch):
        """Test untrack non-existent project shows error."""
        # Mock CLI args
        import sys
        monkeypatch.setattr(sys, 'argv', [
            'warden.py', '--yes', 'project', 'untrack', 'nonexistent'
        ])

        # Run CLI with mocked manager
        from warden import main
        with patch('warden.WardenManager') as mock_manager_class:
            mock_manager_class.return_value = manager
            with patch('warden.AutoUpdater') as mock_updater:
                mock_updater.return_value.should_check_for_updates.return_value = False
                with patch('builtins.print') as mock_print:
                    result = main()

        assert result == 1

        # Verify error message
        output = ' '.join([str(call[0][0]) for call in mock_print.call_args_list])
        assert 'ERROR' in output
        assert 'not found' in output

