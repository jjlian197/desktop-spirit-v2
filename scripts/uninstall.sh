#!/bin/bash
#
# Sherry Desktop Sprite - Uninstallation Script
# 🐱💜 Removes Sherry from macOS launchd
#

set -e

LAUNCHD_NAME="com.sherry.sprite"
LAUNCHD_DEST="$HOME/Library/LaunchAgents/$LAUNCHD_NAME.plist"

echo "🐱💜 Sherry Desktop Sprite Uninstaller"
echo "======================================"
echo ""

# Stop the service if running
if launchctl list | grep -q "$LAUNCHD_NAME"; then
    echo "🛑 Stopping Sherry service..."
    launchctl stop "$LAUNCHD_NAME" 2>/dev/null || true
    launchctl unload "$LAUNCHD_DEST" 2>/dev/null || true
    echo "   Service stopped"
else
    echo "ℹ️  Service not running"
fi

# Remove plist file
if [ -f "$LAUNCHD_DEST" ]; then
    echo "🗑️  Removing launchd plist..."
    rm "$LAUNCHD_DEST"
    echo "   Plist removed"
fi

echo ""
echo "✅ Uninstallation complete!"
echo ""
echo "Sherry has been removed from your system."
echo ""
echo "Note: Log files in ~/.sherry/ were not removed."
echo "      You can delete them manually if desired."
echo ""
echo "💜 Goodbye~ Thanks for having me, Master!"
