#!/bin/bash
# Development environment setup script for AgentSync

set -e  # Exit on error

echo "Setting up AgentSync development environment..."
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1)
    if [ "$PYTHON_VERSION" -ge 3 ]; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python 3 is required but not found"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

echo "[OK] Found Python: $($PYTHON_CMD --version)"
echo ""

# Track if this is a fresh setup
FRESH_SETUP=false

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "[OK] Virtual environment created"
    FRESH_SETUP=true
else
    echo "[OK] Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "[SETUP] Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "[SETUP] Upgrading pip..."
pip install --upgrade pip --quiet

# Install development dependencies
echo "[SETUP] Installing development dependencies..."
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt --quiet
    echo "[OK] Development dependencies installed"
else
    echo "[WARNING] requirements-dev.txt not found"
fi
echo ""

# Install git hooks
echo "[SETUP] Installing git hooks..."
if [ -f "install-hooks.sh" ]; then
    ./install-hooks.sh > /dev/null 2>&1
    echo "[OK] Git hooks installed"
else
    echo "[WARNING] install-hooks.sh not found"
fi
echo ""

# Run tests only on fresh setup
if [ "$FRESH_SETUP" = true ]; then
    echo "[TEST] Running tests to verify setup..."
    if command -v pytest &> /dev/null; then
        pytest --quiet
        echo "[OK] All tests passed"
    else
        echo "[WARNING] pytest not found, skipping tests"
    fi
    echo ""
fi

# Summary
if [ "$FRESH_SETUP" = true ]; then
    echo "[SUCCESS] Development environment setup complete!"
    echo ""
    echo "Next steps:"
    echo "   1. The virtual environment is already activated in this shell"
    echo "   2. Start developing!"
    echo ""
    echo "   Common commands:"
    echo "      pytest              # Run tests"
    echo "      ruff check .        # Check code quality"
    echo "      ruff check --fix .  # Auto-fix issues"
    echo ""
    echo "Tip: To activate the environment in a new shell, run:"
    echo "     source .venv/bin/activate"
else
    echo "[SUCCESS] Development environment refreshed!"
    echo ""
    echo "Updates applied:"
    echo "   - pip upgraded to latest version"
    echo "   - Development dependencies updated"
    echo "   - Virtual environment activated"
    echo ""
    echo "Tip: Run 'pytest' to verify everything works"
fi

