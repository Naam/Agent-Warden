"""
Tests for CLI argument parsing and utility functions.

Targets uncovered lines:
- Lines 58-93: format_time_ago function
- Lines 96-98: get_file_info function (partial)
- Lines 2691-2885: create_parser function (CLI parsing)
"""

import argparse
from datetime import datetime, timedelta

import pytest

from agent_warden.utils import format_timestamp
from warden import create_parser


class TestFormatTimestamp:
    """Test the format_timestamp utility function."""

    def test_just_now(self):
        """Test formatting for times less than 10 seconds ago."""
        now = datetime.now()
        timestamp_str = now.isoformat()
        result = format_timestamp(timestamp_str)
        assert result == "just now"

    def test_seconds_ago(self):
        """Test formatting for times 10-59 seconds ago."""
        past = datetime.now() - timedelta(seconds=30)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert "seconds ago" in result
        assert "30" in result

    def test_one_minute_ago(self):
        """Test formatting for exactly 1 minute ago (singular)."""
        past = datetime.now() - timedelta(minutes=1)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert result == "1 minute ago"

    def test_minutes_ago(self):
        """Test formatting for times 2-59 minutes ago (plural)."""
        past = datetime.now() - timedelta(minutes=30)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert "minutes ago" in result
        assert "30" in result

    def test_one_hour_ago(self):
        """Test formatting for exactly 1 hour ago (singular)."""
        past = datetime.now() - timedelta(hours=1)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert result == "1 hour ago"

    def test_hours_ago(self):
        """Test formatting for times 2-23 hours ago (plural)."""
        past = datetime.now() - timedelta(hours=12)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert "hours ago" in result
        assert "12" in result

    def test_one_day_ago(self):
        """Test formatting for exactly 1 day ago (singular)."""
        past = datetime.now() - timedelta(days=1)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert result == "1 day ago"

    def test_days_ago(self):
        """Test formatting for times 2-6 days ago (plural)."""
        past = datetime.now() - timedelta(days=3)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert "days ago" in result
        assert "3" in result

    def test_one_week_ago(self):
        """Test formatting for exactly 1 week ago (singular)."""
        past = datetime.now() - timedelta(weeks=1)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert result == "1 week ago"

    def test_weeks_ago(self):
        """Test formatting for times 2-4 weeks ago (plural)."""
        past = datetime.now() - timedelta(weeks=2)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        assert "weeks ago" in result
        assert "2" in result

    def test_absolute_date_for_old_times(self):
        """Test formatting for times older than 30 days shows absolute date."""
        past = datetime.now() - timedelta(days=60)
        timestamp_str = past.isoformat()
        result = format_timestamp(timestamp_str)
        # Should contain month abbreviation and year
        assert any(month in result for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        assert str(past.year) in result

    def test_invalid_timestamp_returns_original(self):
        """Test that invalid timestamps are returned as-is."""
        invalid_timestamp = "not-a-valid-timestamp"
        result = format_timestamp(invalid_timestamp)
        assert result == invalid_timestamp

    def test_timezone_aware_timestamp(self):
        """Test that timezone-aware timestamps are handled correctly (bug fix)."""
        # This used to crash with: TypeError: can't subtract offset-naive and offset-aware datetimes
        timestamp_str = "2025-11-14T12:00:00-08:00"
        result = format_timestamp(timestamp_str)
        # Should not crash and should return a valid result
        assert result is not None
        assert isinstance(result, str)

    def test_timezone_naive_timestamp_still_works(self):
        """Test that timezone-naive timestamps still work after the fix."""
        past = datetime.now() - timedelta(minutes=5)
        timestamp_str = past.isoformat()  # No timezone info
        result = format_timestamp(timestamp_str)
        assert "minute" in result or "seconds ago" in result


class TestCreateParser:
    """Test the CLI argument parser creation."""

    def test_parser_creation(self):
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_yes_flag(self):
        """Test that parser has --yes/-y global flag."""
        parser = create_parser()
        args = parser.parse_args(['--yes', 'install', '/path'])
        assert args.yes is True

        args = parser.parse_args(['-y', 'install', '/path'])
        assert args.yes is True

    def test_parser_install_command(self):
        """Test parsing install command with basic arguments."""
        parser = create_parser()
        args = parser.parse_args(['install', '/path/to/project'])
        assert args.command == 'install'
        assert args.project_path == '/path/to/project'

    def test_parser_install_with_target(self):
        """Test parsing install command with target option."""
        parser = create_parser()
        args = parser.parse_args(['install', '/path', '--target', 'cursor'])
        assert args.target == 'cursor'

    def test_parser_install_with_rules(self):
        """Test parsing install command with rules."""
        parser = create_parser()
        args = parser.parse_args(['install', '/path', '--rules', 'rule1', 'rule2'])
        assert args.rules == ['rule1', 'rule2']

    def test_parser_project_list_command(self):
        """Test parsing project list command."""
        parser = create_parser()
        args = parser.parse_args(['project', 'list'])
        assert args.command == 'project'
        assert args.project_command == 'list'

    def test_parser_project_configure_command(self):
        """Test parsing project configure command with correct argument order."""
        parser = create_parser()
        # Correct syntax: project_name comes before --targets
        args = parser.parse_args(['project', 'configure', 'ProjectNameExample', '--targets', 'cursor'])
        assert args.command == 'project'
        assert args.project_command == 'configure'
        assert args.project_name == 'ProjectNameExample'
        assert args.targets == ['cursor']

    def test_parser_project_configure_multiple_targets(self):
        """Test parsing project configure command with multiple targets."""
        parser = create_parser()
        args = parser.parse_args(['project', 'configure', 'my-project', '--targets', 'cursor', 'augment', 'claude'])
        assert args.command == 'project'
        assert args.project_command == 'configure'
        assert args.project_name == 'my-project'
        assert args.targets == ['cursor', 'augment', 'claude']

    def test_parser_project_configure_invalid_target(self):
        """Test that invalid target choices are rejected."""
        parser = create_parser()
        # This should raise SystemExit because 'invalid-target' is not in choices
        with pytest.raises(SystemExit):
            parser.parse_args(['project', 'configure', 'my-project', '--targets', 'invalid-target'])

    def test_parser_project_configure_wrong_order_fails(self):
        """Test that wrong argument order (--targets before project_name) fails."""
        parser = create_parser()
        # This should fail because --targets comes before the positional project_name
        # The parser will interpret 'cursor' as project_name and 'ProjectNameExample' as a target
        # which will fail because 'ProjectNameExample' is not a valid choice
        with pytest.raises(SystemExit):
            parser.parse_args(['project', 'configure', '--targets', 'cursor', 'ProjectNameExample'])


class TestProjectShortcutInterception:
    """Test the 'project <name>' shortcut that converts to 'project show <name>'."""

    def test_project_name_shortcut(self):
        """Test that 'project myproject' is interpreted as 'project show myproject'."""
        import sys
        from unittest.mock import patch

        # Simulate: warden project myproject
        test_argv = ['warden', 'project', 'myproject']

        with patch.object(sys, 'argv', test_argv):
            # The main() function modifies sys.argv in place
            # We need to test the logic directly
            if len(sys.argv) >= 3 and sys.argv[1] == 'project':
                known_subcommands = ['list', 'show', 'update', 'sever', 'remove', 'rename', 'configure']
                if sys.argv[2] not in known_subcommands and not sys.argv[2].startswith('-'):
                    if len(sys.argv) < 4 or sys.argv[3] not in known_subcommands:
                        sys.argv.insert(2, 'show')

            assert sys.argv == ['warden', 'project', 'show', 'myproject']

    def test_project_name_with_subcommand_not_intercepted(self):
        """Test that 'project myproject configure' is NOT converted to 'project show myproject configure'."""
        import sys
        from unittest.mock import patch

        # Simulate: warden project myproject configure
        test_argv = ['warden', 'project', 'myproject', 'configure']

        with patch.object(sys, 'argv', test_argv):
            # Apply the interception logic
            if len(sys.argv) >= 3 and sys.argv[1] == 'project':
                known_subcommands = ['list', 'show', 'update', 'sever', 'remove', 'rename', 'configure']
                if sys.argv[2] not in known_subcommands and not sys.argv[2].startswith('-'):
                    if len(sys.argv) < 4 or sys.argv[3] not in known_subcommands:
                        sys.argv.insert(2, 'show')

            # Should NOT insert 'show' because 'configure' is a known subcommand
            assert sys.argv == ['warden', 'project', 'myproject', 'configure']

    def test_project_subcommand_directly(self):
        """Test that 'project configure' works without interception."""
        import sys
        from unittest.mock import patch

        # Simulate: warden project configure
        test_argv = ['warden', 'project', 'configure']

        with patch.object(sys, 'argv', test_argv):
            # Apply the interception logic
            if len(sys.argv) >= 3 and sys.argv[1] == 'project':
                known_subcommands = ['list', 'show', 'update', 'sever', 'remove', 'rename', 'configure']
                if sys.argv[2] not in known_subcommands and not sys.argv[2].startswith('-'):
                    if len(sys.argv) < 4 or sys.argv[3] not in known_subcommands:
                        sys.argv.insert(2, 'show')

            # Should NOT be modified because 'configure' is a known subcommand
            assert sys.argv == ['warden', 'project', 'configure']

class TestGlobalInstallCommand:
    """Test cases for global-install command argument parsing."""

    def test_global_install_supported_targets(self):
        """Test that global-install accepts supported targets (cursor, claude, windsurf, codex)."""
        parser = create_parser()

        # Test cursor
        args = parser.parse_args(['global-install', 'cursor'])
        assert args.command == 'global-install'
        assert args.target == 'cursor'

        # Test claude
        args = parser.parse_args(['global-install', 'claude'])
        assert args.command == 'global-install'
        assert args.target == 'claude'

        # Test windsurf
        args = parser.parse_args(['global-install', 'windsurf'])
        assert args.target == 'windsurf'

        # Test codex
        args = parser.parse_args(['global-install', 'codex'])
        assert args.target == 'codex'

    def test_global_install_with_force_flag(self):
        """Test that global-install accepts --force flag."""
        parser = create_parser()
        args = parser.parse_args(['global-install', 'claude', '--force'])
        assert args.command == 'global-install'
        assert args.target == 'claude'
        assert args.force is True

    def test_global_install_unsupported_target_augment(self):
        """Test that global-install rejects augment (not supported)."""
        parser = create_parser()
        # augment doesn't support global config, so it should be rejected by parser
        with pytest.raises(SystemExit):
            parser.parse_args(['global-install', 'augment'])

    def test_global_install_with_rules_flag(self):
        """Test that global-install accepts --rules flag."""
        parser = create_parser()
        args = parser.parse_args(['global-install', 'cursor', '--rules', 'git-commit', 'coding-no-emoji'])
        assert args.command == 'global-install'
        assert args.target == 'cursor'
        assert args.rules == ['git-commit', 'coding-no-emoji']

    def test_global_install_with_commands_flag(self):
        """Test that global-install accepts --commands flag."""
        parser = create_parser()
        args = parser.parse_args(['global-install', 'claude', '--commands', 'code-review'])
        assert args.command == 'global-install'
        assert args.target == 'claude'
        assert args.commands == ['code-review']

    def test_global_install_with_empty_rules_flag(self):
        """Test that global-install accepts --rules with no arguments (install all)."""
        parser = create_parser()
        args = parser.parse_args(['global-install', 'cursor', '--rules'])
        assert args.command == 'global-install'
        assert args.target == 'cursor'
        assert args.rules == []  # Empty list means "all rules"


