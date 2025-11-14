#!/bin/bash
# Setup isolated test environment for warden development and testing
# This creates a completely separate warden instance for safe testing

set -e

# Default test directory
TEST_DIR="${WARDEN_TEST_HOME:-/tmp/warden-test}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Warden test environment...${NC}"

# Create test directory structure
echo -e "${YELLOW}Creating test directory: ${TEST_DIR}${NC}"
mkdir -p "$TEST_DIR"
mkdir -p "$TEST_DIR/rules"
mkdir -p "$TEST_DIR/commands"
mkdir -p "$TEST_DIR/packages"

# Create minimal mdc.mdc file
echo -e "${YELLOW}Creating test mdc.mdc file...${NC}"
cat > "$TEST_DIR/mdc.mdc" << 'EOF'
---
description: Test MDC format definition
globs: ["**/*.mdc"]
---

# Test MDC Format

This is a minimal MDC file for testing purposes.
EOF

# Create a test rule
echo -e "${YELLOW}Creating test rule...${NC}"
cat > "$TEST_DIR/rules/test-rule.mdc" << 'EOF'
---
description: Test rule for development
globs: ["**/*.{ts,tsx,js,jsx,py}"]
---

# Test Rule

This is a test rule for development and testing.
EOF

# Create a test command
echo -e "${YELLOW}Creating test command...${NC}"
cat > "$TEST_DIR/commands/test-command.md" << 'EOF'
# Test Command

This is a test command for development and testing.

## Usage

Test command usage instructions.
EOF

# Create test projects
echo -e "${YELLOW}Creating test projects...${NC}"
mkdir -p "$TEST_DIR/test-projects/project1"
mkdir -p "$TEST_DIR/test-projects/project2"

# Create README for test environment
cat > "$TEST_DIR/README.md" << 'EOF'
# Warden Test Environment

This is an isolated test environment for warden development.

## Structure

- `mdc.mdc` - Test MDC format file
- `rules/` - Test rules directory
- `commands/` - Test commands directory
- `packages/` - Test packages directory
- `test-projects/` - Sample test projects
- `.warden_config.json` - Test configuration (created on first use)
- `.warden_state.json` - Test state (created on first use)

## Usage

Set the WARDEN_HOME environment variable to use this test environment:

```bash
export WARDEN_HOME=/tmp/warden-test
warden project list
```

Or use it for a single command:

```bash
WARDEN_HOME=/tmp/warden-test warden install ./test-projects/project1 --rules test-rule
```

## Cleanup

To remove this test environment:

```bash
rm -rf /tmp/warden-test
```
EOF

echo -e "${GREEN}✓ Test environment created at: ${TEST_DIR}${NC}"
echo ""
echo -e "${BLUE}To use this test environment:${NC}"
echo -e "  ${YELLOW}export WARDEN_HOME=${TEST_DIR}${NC}"
echo -e "  ${YELLOW}warden project list${NC}"
echo ""
echo -e "${BLUE}Or for a single command:${NC}"
echo -e "  ${YELLOW}WARDEN_HOME=${TEST_DIR} warden project list${NC}"
echo ""
echo -e "${BLUE}Test projects available at:${NC}"
echo -e "  ${YELLOW}${TEST_DIR}/test-projects/project1${NC}"
echo -e "  ${YELLOW}${TEST_DIR}/test-projects/project2${NC}"
echo ""
echo -e "${GREEN}Happy testing! 🧪${NC}"

