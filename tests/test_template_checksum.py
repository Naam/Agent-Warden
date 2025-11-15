"""Tests for command template checksum handling."""

from pathlib import Path

from warden import WardenManager


class TestTemplateChecksumHandling:
    """Test that template-processed commands don't show as user modified."""

    def test_template_command_not_shown_as_modified(self, manager: WardenManager, tmp_path: Path):
        """Test that a template-processed command is not detected as user modified."""
        # Install a project with a command that has template variables
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Install with copy mode (which triggers template processing)
        project = manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=True
        )

        # Check status immediately after installation
        status = manager.check_project_status(project.name)

        # The command should NOT be detected as user modified
        assert len(status['user_modified_commands']) == 0, \
            "Template-processed command incorrectly detected as user modified"
        assert len(status['conflict_commands']) == 0, \
            "Template-processed command incorrectly detected as conflict"

    def test_template_command_actual_modification_detected(self, manager: WardenManager, tmp_path: Path):
        """Test that actual user modifications to template commands ARE detected."""
        # Install a project with a command
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=True
        )

        # Modify the installed command file
        commands_dir = project_dir / '.augment' / 'commands'
        command_file = commands_dir / 'init-rules.md'

        original_content = command_file.read_text()
        modified_content = original_content + "\n\n# User added this comment"
        command_file.write_text(modified_content)

        # Check status
        status = manager.check_project_status(project.name)

        # Now it SHOULD be detected as user modified
        assert len(status['user_modified_commands']) == 1, \
            "Actual user modification not detected"
        assert status['user_modified_commands'][0]['name'] == 'init-rules'

    def test_template_command_source_update_detected(self, manager: WardenManager, tmp_path: Path):
        """Test that source template updates are detected correctly."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=True
        )

        # Simulate source template update by modifying the source file
        source_file = manager.config.commands_path / 'init-rules.md'
        original_content = source_file.read_text()

        # Add a comment to the template
        modified_content = original_content.replace(
            '# Initialize Project Rules',
            '# Initialize Project Rules\n\n<!-- Updated template -->'
        )
        source_file.write_text(modified_content)

        try:
            # Check status
            status = manager.check_project_status(project.name)

            # Should be detected as outdated
            assert len(status['outdated_commands']) == 1, \
                "Source template update not detected"
            assert status['outdated_commands'][0]['name'] == 'init-rules'
        finally:
            # Restore original source file
            source_file.write_text(original_content)

    def test_template_variables_replaced_correctly(self, manager: WardenManager, tmp_path: Path):
        """Test that template variables are replaced with correct values."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=True
        )

        # Read the installed command file
        commands_dir = project_dir / '.augment' / 'commands'
        command_file = commands_dir / 'init-rules.md'
        installed_content = command_file.read_text()

        # Verify template variables were replaced
        assert '{{RULES_DIR}}' not in installed_content, \
            "Template variable {{RULES_DIR}} was not replaced"

        # Verify the actual path is present (relative path)
        expected_path = '.augment/rules/'
        assert expected_path in installed_content, \
            f"Expected rules directory path '{expected_path}' not found in installed command"

    def test_symlink_mode_uses_source_checksum(self, manager: WardenManager, tmp_path: Path):
        """Test that symlink mode uses source file checksum, not processed."""
        # Install a project with symlink mode
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=False  # Symlink mode - but Augment forces copy
        )

        # Check status
        status = manager.check_project_status(project.name)

        # Should not show as modified
        assert len(status['user_modified_commands']) == 0
        assert len(status['conflict_commands']) == 0

    def test_update_preserves_template_processing(self, manager: WardenManager, tmp_path: Path):
        """Test that updating a template command preserves template processing."""
        # Install a project
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        project = manager.install_project(
            project_dir,
            target='augment',
            command_names=['init-rules'],
            install_commands=True,
            use_copy=True
        )

        # Simulate source update
        source_file = manager.config.commands_path / 'init-rules.md'
        original_content = source_file.read_text()
        modified_content = original_content.replace(
            '# Initialize Project Rules',
            '# Initialize Project Rules v2'
        )
        source_file.write_text(modified_content)

        try:
            # Update the project
            manager.update_project_items(project.name, update_all=True)

            # Read the updated installed file
            commands_dir = project_dir / '.augment' / 'commands'
            command_file = commands_dir / 'init-rules.md'
            updated_content = command_file.read_text()

            # Verify template variables are still replaced
            assert '{{RULES_DIR}}' not in updated_content
            expected_path = '.augment/rules/'
            assert expected_path in updated_content

            # Check status - should be up to date now
            status = manager.check_project_status(project.name)
            assert len(status['outdated_commands']) == 0
            assert len(status['user_modified_commands']) == 0
        finally:
            # Restore original
            source_file.write_text(original_content)

