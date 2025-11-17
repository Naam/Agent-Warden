#!/bin/bash
# Setup VHS demo environment for Agent Warden
# This creates a completely isolated demo environment for recording

set -e

# Demo directory
DEMO_DIR="/tmp/warden-demo"
WARDEN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Agent Warden VHS Demo Environment...${NC}"

# Clean up any existing demo environment
if [ -d "$DEMO_DIR" ]; then
    echo -e "${YELLOW}Removing existing demo environment...${NC}"
    rm -rf "$DEMO_DIR"
fi

# Create demo directory structure
echo -e "${YELLOW}Creating demo directory: ${DEMO_DIR}${NC}"
mkdir -p "$DEMO_DIR"
mkdir -p "$DEMO_DIR/rules/example"
mkdir -p "$DEMO_DIR/commands/example"
mkdir -p "$DEMO_DIR/packages"
mkdir -p "$DEMO_DIR/demo-projects/web-app"
mkdir -p "$DEMO_DIR/demo-projects/api-service"
mkdir -p "$DEMO_DIR/demo-projects/mobile-app"

# Copy example rules to example directory
echo -e "${YELLOW}Copying example rules...${NC}"
cp "$WARDEN_ROOT/rules/example/coding-no-emoji.md" "$DEMO_DIR/rules/example/"
cp "$WARDEN_ROOT/rules/example/git-commit.md" "$DEMO_DIR/rules/example/"
cp "$WARDEN_ROOT/rules/example/documentation.md" "$DEMO_DIR/rules/example/"

# Copy example commands to example directory
echo -e "${YELLOW}Copying example commands...${NC}"
cp "$WARDEN_ROOT/commands/example/code-review.md" "$DEMO_DIR/commands/example/"
cp "$WARDEN_ROOT/commands/example/test-gen.md" "$DEMO_DIR/commands/example/"

# Create some dummy files in demo projects to make them look realistic
echo -e "${YELLOW}Creating demo project files...${NC}"
cat > "$DEMO_DIR/demo-projects/web-app/app.py" << 'EOF'
# Web Application
def hello():
    return "Hello World"
EOF

cat > "$DEMO_DIR/demo-projects/api-service/server.py" << 'EOF'
# API Service
def api_handler():
    return {"status": "ok"}
EOF

cat > "$DEMO_DIR/demo-projects/mobile-app/main.py" << 'EOF'
# Mobile App
def start_app():
    print("App started")
EOF

# Create README for demo environment
cat > "$DEMO_DIR/README.md" << 'EOF'
# Agent Warden VHS Demo Environment

This is an isolated demo environment for recording VHS demos.

## Structure

- `rules/example/` - Example rules (to be copied to rules/)
- `commands/example/` - Example commands (to be copied to commands/)
- `demo-projects/` - Sample demo projects
- `.warden_config.json` - Demo configuration (created on first use)
- `.warden_state.json` - Demo state (created on first use)

## Usage

All commands in the VHS demo use:
```bash
export WARDEN_HOME=/tmp/warden-demo
```

## Cleanup

To remove this demo environment:
```bash
rm -rf /tmp/warden-demo
```
EOF

echo -e "${GREEN}✓ Demo environment created at: ${DEMO_DIR}${NC}"
echo ""
echo -e "${BLUE}Demo environment includes:${NC}"
echo -e "  ${YELLOW}• Example rules in rules/example/${NC}"
echo -e "  ${YELLOW}• Example commands in commands/example/${NC}"
echo -e "  ${YELLOW}• 3 demo projects: web-app, api-service, mobile-app${NC}"
echo ""
echo -e "${GREEN}Ready for VHS recording!${NC}"
echo -e "${BLUE}Run: ${YELLOW}vhs vhs-demo/demo.tape${NC}"

