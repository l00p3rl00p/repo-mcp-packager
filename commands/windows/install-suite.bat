@echo off
TITLE MCP Installer
cd /d "%~dp0\..\.."
echo Installing Workforce Nexus (Permanent Tier)...
python bootstrap.py --permanent
pause
