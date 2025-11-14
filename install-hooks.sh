#!/bin/bash
# Install git hooks for AgentSync

set -e

echo "Installing git hooks..."
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "[ERROR] Not in a git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install pre-commit hook
if [ -f hooks/pre-commit ]; then
    cp hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "[OK] Installed pre-commit hook"
else
    echo "[ERROR] hooks/pre-commit not found"
    exit 1
fi

# Install pre-push hook
if [ -f hooks/pre-push ]; then
    cp hooks/pre-push .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    echo "[OK] Installed pre-push hook"
else
    echo "[WARNING] hooks/pre-push not found (optional)"
fi

echo ""
echo "[SUCCESS] Git hooks installed successfully!"
echo ""
echo "The following checks will run before each commit:"
echo "  - Ruff linter (code quality)"
echo "  - Pytest (all tests must pass)"
echo ""
echo "The following protections are active:"
echo "  - Pre-push hook blocks automated pushes to main branch"
echo "  - Feature branches can be pushed freely by AI assistants"
echo ""
echo "To bypass hooks in emergencies (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""

