"""Pytest configuration and fixtures for Agent Warden tests."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from warden import GitHubPackage, WardenConfig, WardenManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def config(temp_dir: Path) -> WardenConfig:
    """Create a test configuration."""
    return WardenConfig(temp_dir)


@pytest.fixture
def manager(temp_dir: Path) -> WardenManager:
    """Create a test manager with temporary directory."""
    # Create required directories and files
    rules_dir = temp_dir / "rules"
    rules_dir.mkdir()

    # Create test rules
    test_rule = rules_dir / "test-rule.md"
    test_rule.write_text("""---
description: Test rule for unit tests
globs: ["**/*.py"]
alwaysApply: true
type: always_apply
---

# Test Rule

This is a test rule for unit tests.
""")

    rule1 = rules_dir / "rule1.md"
    rule1.write_text("""---
description: Rule 1 for testing
globs: ["**/*.py"]
alwaysApply: true
type: always_apply
---

# Rule 1

Test rule 1.
""")

    test = rules_dir / "test.md"
    test.write_text("""---
description: Test rule
globs: ["**/*.py"]
alwaysApply: true
type: always_apply
---

# Test

Test rule.
""")

    test_rule1 = rules_dir / "test-rule1.md"
    test_rule1.write_text("""---
description: Test rule 1
globs: ["**/*.py"]
alwaysApply: true
type: always_apply
---

# Test Rule 1

Test rule 1.
""")

    commands_dir = temp_dir / "commands"
    commands_dir.mkdir()

    test_command = commands_dir / "test-command.md"
    test_command.write_text("""---
description: Test command for unit tests
tags: ["test"]
---

# Test Command

This is a test command for unit tests.
""")

    test_cmd = commands_dir / "test.md"
    test_cmd.write_text("""---
description: Test command
tags: ["test"]
---

# Test

Test command.
""")

    return WardenManager(temp_dir)


@pytest.fixture
def sample_package() -> GitHubPackage:
    """Create a sample GitHub package for testing."""
    return GitHubPackage("testuser", "testrepo", "main")


@pytest.fixture
def mock_git_repo(temp_dir: Path) -> Path:
    """Create a mock git repository structure."""
    repo_dir = temp_dir / "packages" / "testuser-testrepo"
    repo_dir.mkdir(parents=True)

    # Create rules directory
    rules_dir = repo_dir / "rules"
    rules_dir.mkdir()

    # Create sample rules
    (rules_dir / "typescript.md").write_text("""---
description: TypeScript rules
globs: ["**/*.ts", "**/*.tsx"]
alwaysApply: true
type: always_apply
---

# TypeScript Rules
Test TypeScript rules.
""")

    (rules_dir / "react.md").write_text("""---
description: React rules
globs: ["**/*.jsx", "**/*.tsx"]
alwaysApply: true
type: always_apply
---

# React Rules
Test React rules.
""")

    # Create commands directory
    commands_dir = repo_dir / "commands"
    commands_dir.mkdir()

    # Create sample commands
    (commands_dir / "deploy.md").write_text("""---
description: Deploy command
---

# Deploy Command
Test deploy command.
""")

    return repo_dir


@pytest.fixture
def sample_project_dir(temp_dir: Path) -> Path:
    """Create a sample project directory."""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    return project_dir
