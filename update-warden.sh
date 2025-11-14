#!/bin/bash
# Update Agent Warden to the latest version

set -e

echo "🔄 Updating Agent Warden..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Pull latest changes
echo "📥 Pulling latest changes from git..."
git pull --rebase

echo "✅ Agent Warden updated successfully!"
echo ""
echo "The 'warden' command will automatically use the updated code."
echo "No need to reinstall - editable install keeps everything in sync!"

