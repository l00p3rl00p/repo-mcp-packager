# Shesha Clean Room Installer

**The portable wavefront for Git-Packager. High-precision installation, isolation, and bridging.**

This directory provides a "Just Works" installation experience for human operators and automated agents, ensuring a clean and isolated environment across any repository fork.

---

## ⚡ Quick Start (60s)

### 1. Installation (Headless)
For agents and CI/CD:
```bash
python install.py --headless
```

### 2. Installation (Guided)
For human operators:
```bash
python install.py
```

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [MCP Bridge](#-mcp-bridge)
4. [Design Philosophy](#-design-philosophy)
5. [Key Arguments](#-key-arguments)
6. [Documentation](#-documentation)

---

## 🔍 Overview

The Shesha Clean Room Installer is a standalone directory that can be dropped into any project codebase. It intelligently probes the host system, identifies available components (Python, Node, Docker), and allows for elective installation with automated environment configuration.

---

## 🌟 Features

* **Portability**: Standalone directory. Bootstraps from host tools and local workspace.
* **Inventory Awareness**: Scans for Python, Node, and Docker; offers selective installation.
* **Surgical Reversal**: Marker-aware shell configuration cleanup in `uninstall.py`.
* **Wide compatibility**: Logic hardened for Python 3.9+ environments.

---

## 🌉 MCP Bridge

**Turn any code into AI-accessible tools:**

```bash
# Attach existing MCP server to your IDEs
python install.py --attach-to all

# Wrap legacy script + attach to Claude
python install.py --generate-bridge --attach-to claude
```

The bridge generator creates an `mcp_server.py` wrapper that exposes your script's functions as MCP tools.

---

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

---

## ⚙️ Key Arguments

| Flag | Description |
|---|---|
| `--headless` | Bypass all interactive prompts (agent mode). |
| `--no-gui` | Skip GUI/NPM installation phase. |
| `--npm-policy {local,global,auto}` | Control Node/NPM isolation. |
| `--docker-policy {skip,fail}` | Define behavior if Docker is missing. |

## 🔌 Bonus: MCP JSON Injector

**Standalone tool for adding MCP servers to any IDE config file.**

```bash
# Install (from repo root)
./mcp_injector_install.sh

# Use
mcp-inject --client claude --add    # Interactive mode
mcp-inject --list-clients            # Show all IDE locations
```

See [MCP_INJECTOR_README.md](../MCP_INJECTOR_README.md) for details.

---
**Status**: Production-ready for agent-driven replication.

# MCP Injector
For this to work really well, we recommmden usind mcp-injector_install.sh to install the MCP injector. This will create a mcp-inject binary in your PATH. This will allow you to add MCP servers to any IDE config file. 

THis is located at the repo https://github.com/l00pe3mcp-injector

---

## 📚 Documentation

* [USER_OUTCOMES.md](./USER_OUTCOMES.md): Mission and success metrics.
* [ARCHITECTURE.md](./ARCHITECTURE.md): Technical logic and developer workflow.
* [ENVIRONMENT.md](./ENVIRONMENT.md): Requirements and audit logic.
* [CHANGELOG.md](./CHANGELOG.md): History of fixes.