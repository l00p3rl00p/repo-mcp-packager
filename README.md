# Git Repo MCP Converter & Installer

**A "Just Works" installation experience for converting any repository into an MCP-ready toolset.**

`repo-mcp-packager` provides automation for installing, packaging, and bridging existing code as MCP servers. It ensures clean, isolated environments across any repository fork.

---

## ⚡ Quick Start (60s)

### 1. Bootstrap Workspace
The recommended way to get started is by bootstrapping the full Git-Packager workspace:
```bash
python bootstrap.py
```

### 2. Manual Installation
Alternatively, run the installer directly in any repository:
```bash
python serverinstaller/install.py
```

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [MCP Bridge](#-mcp-bridge)
4. [Design Philosophy](#-design-philosophy)
5. [Key Arguments](#-key-arguments)
6. [Documentation](#-documentation)
7. [Git-Packager Workspace](#-git-packager-workspace)
8. [Contributing](#-contributing)
9. [License](#-license)

---

## 🔍 Overview

This project implements a portal installer that converts any repository into an MCP server. It is designed to be "entry point agnostic," meaning you can drop the `/serverinstaller` directory into any codebase and it will intelligently detect the environment and offer a clean path to deployment.

The converter handles Python, Node, and Docker services, providing a surgical reversal (uninstall) that leaves the host system exactly as it was found.

---

## 🌟 Features

* **Portability**: Standalone directory that bootstraps from host tools.
* **Inventory Awareness**: Probes and identifies components (Python, Node, Docker) automatically.
* **Surgical Reversal**: Marker-aware cleanup of Path and shell configurations.
* **MCP Bridge**: Converts legacy automation scripts into AI-accessible MCP tools.
* **Headless Mode**: Zero-touch replication for automated agents.

---

## 🌉 MCP Bridge

**Turn any legacy code into AI-accessible tools instantly:**

```bash
# Attach existing MCP server to your IDEs
python install.py --attach-to all

# Wrap legacy script + attach to Claude
python install.py --generate-bridge --attach-to claude

# Detect available IDEs
python attach.py --detect
```

The bridge generator scans your scripts for execution blocks and creates a wrapper that exposes functions as MCP tools.

---

## 💡 Philosophy: Not Every Repo Is a Product

The installer understands that code exists on a spectrum. It respects minimalism:
* **Respect Minimalism**: Don't force a `.venv` on a script that doesn't need one.
* **Offer Transition Paths**: Simple scripts can be "upgraded" to full packages later.
* **Enable Portability**: Whether it's a `.sh` wrapper or a full package, the result should be copy-pasteable.

> *"The best installer is the one that knows when to do nothing."*

---

## ⚙️ Key Arguments

| Flag | Description |
|---|---|
| `--headless` | Bypass all interactive prompts (agent mode). |
| `--no-gui` | Skip GUI/NPM installation phase. |
| `--npm-policy {local,global,auto}` | Control Node/NPM isolation. |
| `--docker-policy {skip,fail}` | Define behavior if Docker is missing. |

---

## 📚 Documentation

Detailed documentation is available in the following files:
* [USER_OUTCOMES.md](./USER_OUTCOMES.md): Mission statement and success criteria.
* [ARCHITECTURE.md](./ARCHITECTURE.md): Technical logic and internal modular design.
* [ENVIRONMENT.md](./ENVIRONMENT.md): Requirements and audit logic.
* [CHANGELOG.md](./CHANGELOG.md): History of improvements.

---

## 🤝 Git-Packager Workspace

This tool acts as the **orchestrator** for the complete suite:

| Tool | Purpose |
|------|--------|
| **mcp-injector** | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | Discover and track MCP servers across your system |
| **repo-mcp-packager** (this tool) | Install and package MCP servers with automation |

### Integrated Benefits
* **mcpinv-bootstrap**: Native support for fetching and aligning all 3 tools.
* **Validation**: Automatically validates server health after installation.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## 📝 License

This project is open-source. See LICENSE for details.

---

## 🏁 Status
**Production-ready** for agent-driven replication.
