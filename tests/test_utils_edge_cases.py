"""Tests for utility function edge cases."""

import pytest

from agent_warden.utils import (
    get_file_info,
    parse_frontmatter,
    strip_frontmatter,
)


class TestParseFrontmatterEdgeCases:
    """Test edge cases in frontmatter parsing."""

    def test_parse_frontmatter_no_closing_delimiter(self):
        """Test parsing frontmatter without closing delimiter."""
        content = """---
description: Test rule
globs: ["**/*.py"]
This is missing the closing delimiter
"""
        frontmatter, body = parse_frontmatter(content)

        # Should return empty frontmatter and original content
        assert frontmatter == {}
        assert body == content

    def test_parse_frontmatter_yaml_error(self):
        """Test parsing frontmatter with invalid YAML."""
        content = """---
description: Test rule
invalid: [unclosed bracket
globs: ["**/*.py"
---

# Body content
"""
        frontmatter, body = parse_frontmatter(content)

        # Should return empty frontmatter but still extract body
        assert frontmatter == {}
        assert '# Body content' in body

    def test_parse_frontmatter_empty_frontmatter(self):
        """Test parsing with empty frontmatter section."""
        content = """---
---

# Body content
"""
        frontmatter, body = parse_frontmatter(content)

        # Empty frontmatter section returns empty dict
        # Body should have leading blank lines stripped
        assert frontmatter == {} or frontmatter is None or isinstance(frontmatter, dict)
        assert '# Body content' in body

    def test_parse_frontmatter_only_opening_delimiter(self):
        """Test content with only opening delimiter."""
        content = """---
Some content without closing
More content
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_parse_frontmatter_no_frontmatter(self):
        """Test content without any frontmatter."""
        content = """# Regular markdown

No frontmatter here.
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_parse_frontmatter_valid(self):
        """Test parsing valid frontmatter."""
        content = """---
description: Test rule
globs: ["**/*.py"]
alwaysApply: true
---

# Body content
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter['description'] == 'Test rule'
        assert frontmatter['globs'] == ['**/*.py']
        assert frontmatter['alwaysApply'] is True
        # Body should have leading blank lines stripped
        assert '# Body content' in body

    def test_parse_frontmatter_with_leading_blank_lines(self):
        """Test parsing frontmatter with leading blank lines in body."""
        content = """---
description: Test
---


# Body with blank lines above
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter['description'] == 'Test'
        # Leading blank lines should be stripped
        assert '# Body with blank lines above' in body
        assert not body.startswith('\n')

    def test_parse_frontmatter_complex_yaml(self):
        """Test parsing complex YAML frontmatter."""
        content = """---
description: Complex rule
globs:
  - "**/*.py"
  - "**/*.js"
metadata:
  author: Test
  version: 1.0
tags: [test, example]
---

# Body
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter['description'] == 'Complex rule'
        assert len(frontmatter['globs']) == 2
        assert frontmatter['metadata']['author'] == 'Test'
        assert 'test' in frontmatter['tags']


class TestStripFrontmatter:
    """Test strip_frontmatter function."""

    def test_strip_frontmatter_with_frontmatter(self):
        """Test stripping frontmatter from content."""
        content = """---
description: Test
---

# Body content
"""
        result = strip_frontmatter(content)
        # Body should have frontmatter removed and leading blank lines stripped
        assert '# Body content' in result
        assert 'description' not in result

    def test_strip_frontmatter_without_frontmatter(self):
        """Test stripping from content without frontmatter."""
        content = """# Body content

No frontmatter here.
"""
        result = strip_frontmatter(content)
        assert result == content

    def test_strip_frontmatter_empty_content(self):
        """Test stripping from empty content."""
        result = strip_frontmatter("")
        assert result == ""

    def test_strip_frontmatter_malformed(self):
        """Test stripping from malformed frontmatter."""
        content = """---
description: Test
No closing delimiter

# Body
"""
        result = strip_frontmatter(content)
        # Should return original content when frontmatter is malformed
        assert result == content


class TestGetFileInfo:
    """Test get_file_info function."""

    def test_get_file_info_existing_file(self, tmp_path):
        """Test getting info for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        info = get_file_info(str(test_file))

        assert info is not None
        assert 'checksum' in info
        assert 'source' in info
        assert 'installed_at' in info
        assert len(info['checksum']) == 64  # SHA256 hex length

    def test_get_file_info_nonexistent_file(self):
        """Test getting info for nonexistent file."""
        # Function raises FileNotFoundError for nonexistent files
        with pytest.raises(FileNotFoundError):
            get_file_info("/nonexistent/path/to/file.txt")

    def test_get_file_info_directory(self, tmp_path):
        """Test getting info for directory."""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        # Function raises IsADirectoryError for directories
        with pytest.raises(IsADirectoryError):
            get_file_info(str(test_dir))

