# The Activator: Features & Commands

## Overview
**The Activator (`repo-mcp-packager`)** is the universal installer for the Workforce Nexus. Its philosophy is "Clean Room Installation": it sets up everything a tool needs (venv, dependencies, environment) without polluting your global system.

## Features

### 1. 📦 Universal Installation
*   **Python Projects**: Detects `pyproject.toml` or `requirements.txt`, creates `.venv`, installs deps.
*   **Node.js Projects**: Detects `package.json`, installs `node_modules`.
*   **Simple Scripts**: Wraps single `.py` files with a lightweight `install.sh` shim.
*   **Documents**: Offers to turn any folder of files into a Knowledge Base.

### 2. 🛡️ Clean Room Policy
*   **Isolation**: Always favors local virtual environments.
*   **Surgical PATH**: Adds to `$PATH` with start/end markers in `.zshrc`/`.bashrc` for easy removal.
*   **Uninstall**: `uninstall.py` removes artifacts listed in `.librarian/manifest.json`.

### 3. 🌉 MCP Integration
*   **Bridge Generation**: Can wrap legacy Python scripts in an MCP server (The Bridge).
*   **Attachment**: Connects installed tools to Claude, Cursor, and other IDEs via `mcp-injector`.
*   **Knowledge Base**: One-click setup of the Librarian alongside your code.

## Command Reference

### Installation
```bash
# Standard interactive install
python install.py

# Headless check (good for CI/automation)
python install.py --headless

# Install with Knowledge Base
python install.py --with-library
```

### Management
```bash
# Update the installation
python install.py --update

# Uninstall everything
python uninstall.py
```

### Advanced
```bash
# Attach to all IDEs during install
python install.py --attach-to all

# Generate MCP Bridge for legacy code
python install.py --generate-bridge
```

---
**Part of the Workforce Nexus**
*   **The Surgeon**: `mcp-injector` (Configuration)
*   **The Observer**: `mcp-server-manager` (Dashboard)
*   **The Activator**: `repo-mcp-packager` (Automation)
*   **The Librarian**: `mcp-link-library` (Knowledge)
