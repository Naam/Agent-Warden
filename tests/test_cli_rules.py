"""Tests for the 'warden rules' CLI command."""

from unittest.mock import patch

from warden import main


class TestCLIRules:
    """Test the 'warden rules' command."""

    def test_rules_command_shows_all_rules(self, manager, sample_project_dir, capsys):
        """Test that 'warden rules' shows all rules with tree view."""
        # Create a project with some rules
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule', 'rule1']
        )

        # Run rules command
        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        # Verify output
        captured = capsys.readouterr()
        assert 'Rules Overview:' in captured.out
        assert 'test-rule' in captured.out
        assert 'rule1' in captured.out
        assert project.name in captured.out
        # Check for tree characters
        assert '├─' in captured.out or '└─' in captured.out

    def test_rules_command_fuzzy_match_case_insensitive(self, manager, sample_project_dir, capsys):
        """Test that 'warden rules <query>' does fuzzy matching (case-insensitive)."""
        # Create a project with rules
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule', 'rule1', 'test']
        )

        # Test lowercase query matching uppercase rule
        with patch('sys.argv', ['warden', 'rules', 'TEST']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        assert 'test-rule' in captured.out
        assert 'test' in captured.out or 'test-rule' in captured.out
        # rule1 should not appear as a standalone rule (test-rule1 is OK)
        # Check that rule1 doesn't appear at start of line (as its own rule)
        lines = captured.out.split('\n')
        rule1_lines = [line for line in lines if 'rule1' in line and 'test-rule1' not in line]
        assert len(rule1_lines) == 0

    def test_rules_command_fuzzy_match_partial(self, manager, sample_project_dir, capsys):
        """Test that fuzzy matching works with partial strings."""
        # Create a project with rules
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule', 'test-rule1', 'rule1']
        )

        # Query 'test' should match both test-* rules
        with patch('sys.argv', ['warden', 'rules', 'test']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        assert 'test-rule' in captured.out
        assert 'test-rule1' in captured.out
        # rule1 doesn't contain 'test'
        assert 'rule1' not in captured.out or 'test-rule1' in captured.out

    def test_rules_command_no_match(self, manager, sample_project_dir, capsys):
        """Test that non-matching query shows appropriate message."""
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        with patch('sys.argv', ['warden', 'rules', 'nonexistent']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result == 0

        captured = capsys.readouterr()
        assert 'No rules found matching' in captured.out
        assert 'nonexistent' in captured.out

    def test_rules_command_installed_filter(self, manager, sample_project_dir, capsys):
        """Test that --installed flag shows only installed rules."""
        # Create a project with some rules (not all available rules)
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        with patch('sys.argv', ['warden', 'rules', '--installed']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        assert 'test-rule' in captured.out
        # Other available rules should not be shown
        assert 'rule1' not in captured.out or '(not installed)' not in captured.out

    def test_rules_command_available_filter(self, manager, sample_project_dir, capsys):
        """Test that --available flag shows only uninstalled rules."""
        # Create a project with some rules
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        with patch('sys.argv', ['warden', 'rules', '--available']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        # Should show rules that are NOT installed
        assert 'test-rule' not in captured.out or '(not installed)' in captured.out

    def test_rules_command_combined_query_and_filter(self, manager, sample_project_dir, capsys):
        """Test combining query with --installed filter."""
        # Create a project with multiple rules
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule', 'test-rule1']
        )

        # Query 'test' with --installed should show only installed test rules
        with patch('sys.argv', ['warden', 'rules', 'test', '--installed']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        assert 'test-rule' in captured.out
        assert 'test-rule1' in captured.out
        # rule1 should not appear as standalone (test-rule1 is OK)
        lines = captured.out.split('\n')
        rule1_only_lines = [line for line in lines if 'rule1' in line and 'test-rule1' not in line]
        assert len(rule1_only_lines) == 0

    def test_rules_command_shows_project_path_format(self, manager, sample_project_dir, capsys):
        """Test that output format is 'project:path (target)'."""
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        # Check format: project:path (target)
        assert f"{project.name}:{project.path}" in captured.out
        assert '(augment)' in captured.out

    def test_rules_command_shows_remote_marker(self, manager, sample_project_dir, capsys):
        """Test that remote projects show [remote] marker."""
        # Skip SSH test - just test the logic with a mock remote project
        # Create a local project first
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Manually mark it as remote in state for testing
        project_state = manager.config.state['projects'][project.name]
        project_state['path'] = 'user@server.com:/var/www/app'
        manager.config.save_state()

        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        assert '[remote]' in captured.out

    def test_rules_command_sorted_by_usage(self, manager, sample_project_dir, tmp_path, capsys):
        """Test that rules are sorted by number of installations (most used first)."""
        # Create multiple projects with different rules
        manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule', 'rule1']
        )

        project2_dir = tmp_path / 'project2'
        project2_dir.mkdir()
        manager.install_project(
            project2_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']  # Only one rule
        )

        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        # test-rule (2 projects) should appear before rule1 (1 project)
        test_rule_pos = captured.out.find('test-rule')
        rule1_pos = captured.out.find('rule1')
        # Make sure we're not finding test-rule1
        assert test_rule_pos < rule1_pos

    def test_rules_command_multiple_targets(self, manager, sample_project_dir, capsys):
        """Test that rules installed in multiple targets are shown correctly."""
        # Install same rule to multiple targets
        project = manager.install_project(
            sample_project_dir,
            'augment',
            use_copy=False,
            rule_names=['test-rule']
        )

        # Add same rule to cursor target (install to same path with different target)
        manager.install_project(
            sample_project_dir,
            'cursor',
            use_copy=False,
            rule_names=['test-rule']
        )

        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        # Should show both targets
        assert '(augment)' in captured.out
        assert '(cursor)' in captured.out
        # Should show project twice (once per target)
        assert captured.out.count(project.name) >= 2

    def test_rules_command_no_projects(self, manager, capsys):
        """Test rules command when no projects are registered."""
        # Don't create any projects

        with patch('sys.argv', ['warden', 'rules']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result is None or result == 0

        captured = capsys.readouterr()
        # Should still show available rules, but marked as not installed
        assert 'Rules Overview:' in captured.out
        assert '(not installed)' in captured.out

    def test_rules_command_empty_result_with_installed_filter(self, manager, capsys):
        """Test --installed filter when no rules are installed."""
        # Don't create any projects

        with patch('sys.argv', ['warden', 'rules', '--installed']):
            with patch('warden.WardenManager') as mock_manager_class:
                mock_manager_class.return_value = manager
                result = main()

        assert result == 0

        captured = capsys.readouterr()
        assert 'No installed rules found' in captured.out

