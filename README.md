# Git Repo and Git Repo MCP Converter and Installer
 This directory provides a "Just Works" installation experience for human operators and automated agents, ensuring a clean and isolated environment across any repository fork.

 ## Convert any REPO into an MPC server (with options)

* installs any ".sh" file with option (see below)
* Installs any git repo
* Installs any git repo as a MCP server
  * if run with https://github.com/l00p3rl00p/mcp-injector/  in root it i also injects the MCP config files into common areas
 


 
## 🚀 Quick Start (60s)
## Quick Start

### Bootstrap the Workspace (Recommended)

```bash
python bootstrap.py
```

This will check for and optionally fetch the other Git-Packager components (`mcp-injector`, `mcp-server-manager`) to enable the full suite of functionality.

### Manual Installation

```bash
python serverinstaller/install.py
```

## 🛠 Features

- **Portability**: Standalone directory. Bootstraps from host tools and local workspace.
- **Inventory Awareness**: Scans for Python, Node, and Docker; offers selective installation.
- **Surgical Reversal**: Clean uninstall including marker-aware shell configuration cleanup.
- **Wide compatibility**: Logic hardened for Python 3.9+ environments.
- **MCP Bridge**: Wrap legacy code as MCP servers and auto-attach to IDEs.

## 🌉 MCP Bridge (New!)

**Turn any code into AI-accessible tools:**

```bash
# Attach existing MCP server to your IDEs
python install.py --attach-to all

# Wrap legacy script + attach to Claude
python install.py --generate-bridge --attach-to claude

# Detect available IDEs
python attach.py --detect
```

See [Walkthrough](../../../.gemini/antigravity/brain/bf0a76d8-2b11-4080-94bb-966b65692a6b/walkthrough.md) for details.

## 📖 Documentation

- [USER_OUTCOMES.md](./USER_OUTCOMES.md): Why we built this and how we measure success.
- [ARCHITECTURE.md](./ARCHITECTURE.md): Technical logic, modular scripts, and developer workflow.
- [ENVIRONMENT.md](./ENVIRONMENT.md): Environment requirements, audit logic, and policies.
- [CHANGELOG.md](./CHANGELOG.md): History of improvements and fixes.

## 💡 Philosophy: Not Every Repo Is a Product

The installer understands that **not every directory with code needs to be a full-blown installable package.**

### The Spectrum of Code
```
Simple Script ─────────── Tool ─────────── Full Product
mcp_injector.py      Shesha CLI      Shesha RLM (Server + GUI)
```

When you run `python serverinstaller/install.py`, the installer **detects** what kind of repo it's in:

**Simple Script Detected:**
```
Options:
  1. Create install.sh wrapper (lightweight, recommended)
  2. Package as full Python project (pyproject.toml + .venv)
  3. Exit (leave as-is)
```

**Design Principles:**
- **Respect Minimalism**: Don't force a `.venv` on a script that doesn't need one
- **Offer Transition Paths**: Simple scripts can be "upgraded" to full packages later
- **Enable Portability**: Whether it's a `.sh` wrapper or full package, the result is copy-pasteable

> *"The best installer is the one that knows when to do nothing."*


## ⚙️ Key Arguments

| Flag | Description |
|---|---|
| `--headless` | Bypass all interactive prompts (agent mode). |
| `--no-gui` | Skip GUI/NPM installation phase. |
| `--npm-policy {local,global,auto}` | Control Node/NPM isolation. |
| `--docker-policy {skip,fail}` | Define behavior if Docker is missing. |

## 🔌 MCP JSON Injector Integration

**Add automatic MCP config file management to this project.**

Get the [MCP Injector](https://github.com/l00p3rl00p/mcp-injector/) and drop it in the root of this repository to enable:
- **Auto-update** MCP config files across all supported IDEs
- **Safe configuration** with automatic backup and JSON validation
- **Interactive setup** for adding/removing MCP servers

```bash
# Once mcp_injector.py is in the root:
python mcp_injector.py --client claude --add    # Interactive mode
python mcp_injector.py --list-clients           # Show all IDE locations
```

This integration enables the installer to automatically configure MCP servers in Claude, Xcode, and other supported IDEs without manual JSON editing.

---
**Status**: Production-ready for agent-driven replication.

---

## 🤝 Better Together: Git-Packager Workspace

This tool is the **orchestrator** of the Git-Packager workspace:

| Tool | Purpose |
|------|--------|
| **mcp-injector** | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | Discover and track MCP servers across your system |
| **repo-mcp-packager** (this tool) | Install and package MCP servers with automation |

### Standalone vs. Integrated

- **Standalone**: Works perfectly for installing individual MCP servers.
- **Integrated**: The full workspace provides:
  - Automatic IDE configuration via `mcp-injector`
  - Server discovery and tracking via `mcp-server-manager`
  - One-command workspace setup via `python bootstrap.py`

### Bootstrap the Complete Workspace

```bash
python bootstrap.py
```

This checks for missing Git-Packager components and offers to fetch them from GitHub, giving you the complete suite of tools.
