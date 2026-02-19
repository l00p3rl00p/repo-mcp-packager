#!/bin/bash
# Double-click to sync git workspace to runtime
echo "Starting synchronization..."
mcp-activator --sync
read -p "Press any key to exit..."
