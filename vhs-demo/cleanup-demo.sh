#!/bin/bash
# Cleanup VHS demo environment for Agent Warden

DEMO_DIR="/tmp/warden-demo"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Cleaning up Agent Warden VHS Demo Environment...${NC}"

if [ -d "$DEMO_DIR" ]; then
    echo -e "${YELLOW}Removing demo environment at: ${DEMO_DIR}${NC}"
    rm -rf "$DEMO_DIR"
    echo -e "${GREEN}✓ Demo environment removed${NC}"
else
    echo -e "${RED}Demo environment not found at: ${DEMO_DIR}${NC}"
    echo -e "${YELLOW}Nothing to clean up${NC}"
fi

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"

