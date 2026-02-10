# Architecture - Shesha Clean Room Installer

Technical logic, modular scripts, and developer workflow for the portable clean room installer.

---

## 🔍 Design Principles

* **Entry Point Agnostic**: Any single repo in the workspace can bootstrap the full stack.
* **Radical Isolation**: Prefer local `.venv` and isolated `npm` over host-global changes.
* **Deterministic Reversal**: Every change is logged in a manifest for 100% clean uninstall.

---

## ⚡ Tactile Workflow

### Installation (Guided)
```bash
python install.py
```
*Triggers interactive inventory probes, offers elective component selection, and PATH setup.*

### Installation (Headless)
```bash
python install.py --headless --no-gui
```
*Zero-touch replication for automated agents.*

### Verification & Cleanup
```bash
# Verify installation integrity
python verify.py

# Surgical uninstall
python uninstall.py --kill-venv
```

---

## 📋 Table of Contents
1. [Logic Model & Subsystems](#-logic-model--subsystems)
2. [Standalone Utilities](#-standalone-utilities)
3. [Universal Bootstrap](#-universal-bootstrap)
4. [Constraints & Security](#-constraints--security)

---

## 📂 Logic Model & Subsystems

### 1. Probe Layer (`audit.py`)
Non-destructive detection of Shell, Node, NPM, Docker, and Python environments. Hardened for **Python 3.9+** to ensure robustness on older systems.

### 2. Execution Layer (`install.py`)
Scans parent workspace for markers (`pyproject.toml`, `package.json`), presents an inventory of components, and enforces installation (bootstraps `.venv`, installs dependencies).

### 3. State Management (`manifest.json`)
The registry of every file, directory, or shell configuration change. Essential for achieving zero file-leak cleanup during uninstallation.

---

## 🛠 Standalone Utilities

### MCP JSON Injector (`/mcp_injector.py`)
Pure Python stdlib tool to safely manage IDE config files. Surgical JSON handling prevents "bracket hell" and broken configurations.

### MCP Bridge Generator (`bridge.py`)
Wraps legacy automation code as MCP servers. It scans scripts for execution blocks and generates an `mcp_server.py` wrapper that exposes internal functions as tools.

---

## 🌐 Universal Bootstrap & Mutual Discovery

Implemented via `bootstrap.py`:
1. **Local**: Check for components in the current project root.
2. **Sibling**: Check parent directory for sibling workspace repos.
3. **Remote**: Offer to `git clone` if missing.

---

## 🛡 Constraints & Security

* **Local-First**: Only bootstraps from local state or explicit user-consented clones.
* **Permissions**: Explicitly asks for permission before modifying any host RC files.
* **Resilience**: Subprocess failures (e.g., pip) are captured as warnings to ensure the audit completes.
