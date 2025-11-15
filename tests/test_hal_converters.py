"""Tests for HAL converter edge cases and uncovered code."""


from agent_warden.hal import (
    AgentHAL,
    CodexConverter,
    CursorConverter,
    WindsurfConverter,
    get_hal,
)


class TestCursorConverter:
    """Test CursorConverter edge cases."""

    def test_convert_without_frontmatter(self):
        """Test CursorConverter fallback when no frontmatter is present."""
        converter = CursorConverter()

        # Content without frontmatter
        content = """# Test Rule

This is a rule without frontmatter.
"""

        result = converter.convert(content, {}, content)

        # Should return just the body when no frontmatter
        assert result == content
        assert '---' not in result

    def test_convert_with_frontmatter(self):
        """Test CursorConverter with valid frontmatter."""
        converter = CursorConverter()

        content = """---
description: Test rule
globs: ["**/*.py"]
---

# Test Rule
"""
        frontmatter = {
            'description': 'Test rule',
            'globs': ['**/*.py']
        }
        body = '# Test Rule'

        result = converter.convert(content, frontmatter, body)

        # Should have Cursor-specific frontmatter
        assert '---' in result
        assert 'description' in result
        assert '# Test Rule' in result

    def test_convert_empty_frontmatter(self):
        """Test CursorConverter with empty frontmatter dict."""
        converter = CursorConverter()

        body = '# Test Rule\n\nContent here.'
        result = converter.convert('', {}, body)

        # Should return just body when frontmatter is empty
        assert result == body


class TestWindsurfConverter:
    """Test WindsurfConverter."""

    def test_convert_returns_content_unchanged(self):
        """Test that WindsurfConverter returns content unchanged."""
        converter = WindsurfConverter()

        content = """---
description: Test
---

# Body
"""
        frontmatter = {'description': 'Test'}
        body = '# Body'

        result = converter.convert(content, frontmatter, body)

        # Windsurf uses Augment format, so content should be unchanged
        assert result == content

    def test_windsurf_docs_url(self):
        """Test that WindsurfConverter has no docs URL."""
        converter = WindsurfConverter()
        assert converter.DOCS_URL is None

    def test_windsurf_supported_fields(self):
        """Test WindsurfConverter supported fields."""
        converter = WindsurfConverter()
        assert 'description' in converter.SUPPORTED_FIELDS
        assert 'globs' in converter.SUPPORTED_FIELDS


class TestCodexConverter:
    """Test CodexConverter."""

    def test_convert_returns_content_unchanged(self):
        """Test that CodexConverter returns content unchanged."""
        converter = CodexConverter()

        content = """---
description: Test
---

# Body
"""
        frontmatter = {'description': 'Test'}
        body = '# Body'

        result = converter.convert(content, frontmatter, body)

        # Codex uses Augment format, so content should be unchanged
        assert result == content

    def test_codex_docs_url(self):
        """Test that CodexConverter has no docs URL."""
        converter = CodexConverter()
        assert converter.DOCS_URL is None

    def test_codex_supported_fields(self):
        """Test CodexConverter supported fields."""
        converter = CodexConverter()
        assert 'description' in converter.SUPPORTED_FIELDS
        assert 'globs' in converter.SUPPORTED_FIELDS


class TestAgentHAL:
    """Test AgentHAL methods."""

    def test_get_docs_url_cursor(self):
        """Test getting docs URL for Cursor."""
        hal = AgentHAL()
        url = hal.get_docs_url('cursor')

        assert url is not None
        assert 'cursor' in url.lower() or 'anysphere' in url.lower()

    def test_get_docs_url_augment(self):
        """Test getting docs URL for Augment."""
        hal = AgentHAL()
        url = hal.get_docs_url('augment')

        assert url is not None
        assert 'augment' in url.lower()

    def test_get_docs_url_claude(self):
        """Test getting docs URL for Claude."""
        hal = AgentHAL()
        url = hal.get_docs_url('claude')

        assert url is not None
        assert 'claude' in url.lower() or 'anthropic' in url.lower()

    def test_get_docs_url_windsurf(self):
        """Test getting docs URL for Windsurf (should be None)."""
        hal = AgentHAL()
        url = hal.get_docs_url('windsurf')

        # Windsurf doesn't have public docs yet
        assert url is None

    def test_get_docs_url_codex(self):
        """Test getting docs URL for Codex (should be None)."""
        hal = AgentHAL()
        url = hal.get_docs_url('codex')

        # Codex doesn't have public docs yet
        assert url is None

    def test_get_supported_fields_cursor(self):
        """Test getting supported fields for Cursor."""
        hal = AgentHAL()
        fields = hal.get_supported_fields('cursor')

        assert isinstance(fields, list)
        assert 'description' in fields
        assert 'globs' in fields

    def test_get_supported_fields_augment(self):
        """Test getting supported fields for Augment."""
        hal = AgentHAL()
        fields = hal.get_supported_fields('augment')

        assert isinstance(fields, list)
        assert 'description' in fields
        assert 'globs' in fields

    def test_get_supported_fields_windsurf(self):
        """Test getting supported fields for Windsurf."""
        hal = AgentHAL()
        fields = hal.get_supported_fields('windsurf')

        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_get_supported_fields_codex(self):
        """Test getting supported fields for Codex."""
        hal = AgentHAL()
        fields = hal.get_supported_fields('codex')

        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_get_hal_singleton(self):
        """Test that get_hal returns singleton instance."""
        hal1 = get_hal()
        hal2 = get_hal()

        assert hal1 is hal2

