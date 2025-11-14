#!/bin/bash
# Cleanup warden test environment

set -e

# Default test directory
TEST_DIR="${WARDEN_TEST_HOME:-/tmp/warden-test}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ ! -d "$TEST_DIR" ]; then
    echo -e "${YELLOW}Test environment not found at: ${TEST_DIR}${NC}"
    exit 0
fi

echo -e "${YELLOW}Removing test environment: ${TEST_DIR}${NC}"
rm -rf "$TEST_DIR"

echo -e "${GREEN}✓ Test environment cleaned up${NC}"

# Unset WARDEN_HOME if it points to the test directory
if [ "$WARDEN_HOME" = "$TEST_DIR" ]; then
    echo -e "${YELLOW}Note: WARDEN_HOME is still set to ${TEST_DIR}${NC}"
    echo -e "${YELLOW}Run: unset WARDEN_HOME${NC}"
fi

