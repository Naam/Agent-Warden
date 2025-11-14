# Warden Tests

This directory contains automated tests and manual testing utilities for Agent Warden.

## Quick Start

### Automated Tests (pytest)

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_manager_core.py

# Run with verbose output
pytest tests/ -v
```

### Manual Testing (Isolated Environment)

```bash
# 1. Setup isolated test environment
./tests/setup-test-env.sh

# 2. Use test environment
export WARDEN_HOME=/tmp/warden-test
warden install /tmp/warden-test/test-projects/project1 --rules test-rule
warden status

# 3. Cleanup
./tests/cleanup-test-env.sh
unset WARDEN_HOME
```

## Automated Testing

### Test Files

- `test_backend.py` - File system backend tests (local and remote)
- `test_config.py` - Configuration management tests
- `test_github_package.py` - GitHub package management tests
- `test_manager_core.py` - Core WardenManager functionality tests
- `test_multi_target.py` - Multi-target installation tests
- `test_package_management.py` - Package installation and updates tests
- `test_project_state.py` - Project state management tests
- `test_remote_config.py` - Remote configuration tests
- `test_remote_integration.py` - Remote SSH integration tests
- `test_rename.py` - Project rename functionality tests
- `test_versioning.py` - Checksum-based versioning tests

### Fixtures (conftest.py)

- `temp_dir` - Temporary directory for tests
- `config` - WardenConfig instance with test directory
- `manager` - WardenManager instance with test directory

### Writing Tests

```python
def test_install_project(manager, tmp_path):
    """Test project installation."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    result = manager.install_project(
        project_dir,
        target='augment',
        rule_names=['test-rule']
    )
    
    assert result.name == 'test-project'
    assert result.has_target('augment')
```

## Manual Testing

### WARDEN_HOME Environment Variable

The `WARDEN_HOME` environment variable redirects warden to use a different directory for all configuration, state, rules, and commands. This ensures your production projects are never affected during testing.

### Setup Test Environment

```bash
./tests/setup-test-env.sh
```

Creates `/tmp/warden-test/` with:
- Test configuration and state files
- Sample rules and commands
- Two test projects (project1 and project2)

### Using Test Environment

```bash
# Single command
WARDEN_HOME=/tmp/warden-test warden project list

# Multiple commands
export WARDEN_HOME=/tmp/warden-test
warden install /tmp/warden-test/test-projects/project1 --rules test-rule
warden install /tmp/warden-test/test-projects/project2 --rules test-rule
warden install-all --rules documentation
warden status
```

### Cleanup

```bash
./tests/cleanup-test-env.sh
unset WARDEN_HOME
```

### Custom Test Directory

```bash
WARDEN_TEST_HOME=/tmp/my-test ./tests/setup-test-env.sh
export WARDEN_HOME=/tmp/my-test
warden project list
```

## Safety Rules

**Never:**
- Test against production projects
- Modify production state files
- Run tests without isolation

**Always:**
- Use pytest fixtures for automated tests
- Use `WARDEN_HOME` for manual tests
- Verify production is untouched
- Clean up test artifacts

## Testing Checklist

Before testing any feature:

- [ ] Am I using `WARDEN_HOME` or pytest fixtures?
- [ ] Have I verified production projects won't be affected?
- [ ] Am I testing against `/tmp` or test fixture paths?
- [ ] Will cleanup happen automatically?

## Example: Testing install-all

```bash
# Setup
./tests/setup-test-env.sh
export WARDEN_HOME=/tmp/warden-test

# Install to test projects
warden install /tmp/warden-test/test-projects/project1 --rules test-rule
warden install /tmp/warden-test/test-projects/project2 --rules test-rule

# Test install-all
warden install-all --rules documentation --dry-run
warden install-all --rules documentation

# Verify
warden status

# Cleanup
./tests/cleanup-test-env.sh
unset WARDEN_HOME
```

