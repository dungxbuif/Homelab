#!/bin/bash

# Stop all ktunnel processes
echo "🛑 Stopping all ktunnel tunnels..."

# Find and kill all ktunnel expose processes
PIDS=$(pgrep -f "ktunnel expose" 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo "ℹ️  No active ktunnel tunnels found"
else
    echo "🔍 Found active tunnels (PIDs: $PIDS)"
    echo "$PIDS" | xargs kill
    
    # Wait a moment and check if they're really stopped
    sleep 2
    REMAINING=$(pgrep -f "ktunnel expose" 2>/dev/null || true)
    
    if [ -z "$REMAINING" ]; then
        echo "✅ All tunnels stopped successfully"
    else
        echo "⚠️  Some tunnels still running, force killing..."
        echo "$REMAINING" | xargs kill -9
        echo "✅ All tunnels force stopped"
    fi
fi

# Clean up log files
echo "🧹 Cleaning up log files..."
rm -f /tmp/ktunnel-*.log

echo "🎉 Tunnel cleanup completed!"
