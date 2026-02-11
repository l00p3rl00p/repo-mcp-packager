#!/bin/bash
# Workforce Nexus - GUI Launcher
# Detects the environment (dev workspace vs installed) and launches the GUI.

echo "🚀 Starting Workforce Nexus Dashboard..."

# 1. Try Local Workspace (Dev Mode)
if [ -d "mcp-server-manager" ]; then
    echo "📂 Detected Workspace Mode"
    python3 -m mcp_inventory.cli gui
    exit $?
fi

# 2. Try Installed Nexus (App Mode)
NEXUS_HOME="$HOME/.mcp-tools"
if [ -d "$NEXUS_HOME" ]; then
    echo "🏭 Detected Industrial Nexus Mode"
    # Check for venv
    if [ -f "$NEXUS_HOME/.venv/bin/python" ]; then
        "$NEXUS_HOME/.venv/bin/python" -m mcp_inventory.cli gui
    else
        # Fallback to system python if venv missing (Lite mode)
        python3 -m mcp_inventory.cli gui
    fi
    exit $?
fi

echo "❌ Workforce Nexus not found. Please run bootstrap.py first."
exit 1
