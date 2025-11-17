#!/bin/bash
# Quick script to set up, record, and optionally clean up the VHS demo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Agent Warden VHS Demo Recorder${NC}"
echo ""

# Check if VHS is installed
if ! command -v vhs &> /dev/null; then
    echo -e "${YELLOW}VHS is not installed. Installing via Homebrew...${NC}"
    brew install vhs
fi

# Step 1: Setup
echo -e "${BLUE}Step 1: Setting up demo environment...${NC}"
"$SCRIPT_DIR/setup-demo-env.sh"
echo ""

# Step 2: Record
echo -e "${BLUE}Step 2: Recording demo...${NC}"
cd "$SCRIPT_DIR/.."
vhs "$SCRIPT_DIR/demo.tape"
echo ""

# Step 3: Show result
if [ -f "$SCRIPT_DIR/agent-warden-demo.gif" ]; then
    echo -e "${GREEN}✓ Demo recorded successfully!${NC}"
    echo -e "${BLUE}Output: ${YELLOW}$SCRIPT_DIR/agent-warden-demo.gif${NC}"
    echo ""
    
    # Ask to open
    read -p "Open the demo GIF? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$SCRIPT_DIR/agent-warden-demo.gif"
    fi
    echo ""
    
    # Ask to cleanup
    read -p "Clean up demo environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/cleanup-demo.sh"
    else
        echo -e "${YELLOW}Demo environment kept at: /tmp/warden-vhs-demo${NC}"
        echo -e "${YELLOW}Run ./vhs-demo/cleanup-demo.sh to remove it later${NC}"
    fi
else
    echo -e "${RED}✗ Recording failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Done!${NC}"

