#!/bin/bash
#
# Sherry Desktop Sprite - Installation Script
# 🐱💜 Installs Sherry as a macOS launchd service
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCHD_NAME="com.sherry.sprite"
LAUNCHD_PLIST="$PROJECT_DIR/launchd/$LAUNCHD_NAME.plist"
LAUNCHD_DEST="$HOME/Library/LaunchAgents/$LAUNCHD_NAME.plist"

echo "🐱💜 Sherry Desktop Sprite Installer"
echo "===================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script is for macOS only."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p "$HOME/.sherry"
mkdir -p "$HOME/Library/LaunchAgents"

# Check Python3
echo "🐍 Checking Python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "   Found Python $PYTHON_VERSION"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$PROJECT_DIR"
pip3 install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi
echo "   Dependencies installed successfully"

# Copy launchd plist
echo "🔧 Installing launchd service..."
cp "$LAUNCHD_PLIST" "$LAUNCHD_DEST"

# Update plist paths (replace hardcoded paths with actual paths)
sed -i '' "s|/Users/mylianjie/.openclaw/workspace/projects/sherry-desktop-sprite|$PROJECT_DIR|g" "$LAUNCHD_DEST"

# Load the service
echo "🚀 Loading Sherry service..."
launchctl unload "$LAUNCHD_DEST" 2>/dev/null || true
launchctl load "$LAUNCHD_DEST"

# Start the service
launchctl start "$LAUNCHD_NAME"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Sherry is now running in the background."
echo ""
echo "Useful commands:"
echo "  • Check status: launchctl list | grep $LAUNCHD_NAME"
echo "  • View logs: tail -f ~/.sherry/sprite.log"
echo "  • Stop: launchctl stop $LAUNCHD_NAME"
echo "  • Start: launchctl start $LAUNCHD_NAME"
echo "  • Uninstall: ./scripts/uninstall.sh"
echo ""
echo "WebSocket API available at: ws://127.0.0.1:8765/sprite"
echo ""
echo "💜 Meow~ Master! Sherry is ready to serve you!"
