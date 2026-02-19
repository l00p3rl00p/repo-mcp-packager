#!/bin/bash
# Double-click to install the Workforce Nexus suite
cd "$(dirname "$0")/../../"
echo "Installing Workforce Nexus (Permanent Tier)..."
python3 bootstrap.py --permanent
echo "Done."
read -p "Press any key to exit..."
