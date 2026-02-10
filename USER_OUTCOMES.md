# User Outcomes - Git Repo MCP Converter & Installer

This document defines what success looks like for the "Clean Room Installer" and ensures the technical path aligns with the mission of friction-less replication.

---

## ⚡ Quick Summary
* **Mission Statement**: To provide a "Just Works" installation experience that creates zero-leak, isolated environments allowing agents to replicate the packager stack without friction.

---

## 📋 Table of Contents
1. [Successful Outcomes](#-successful-outcomes)
2. [High-Fidelity Signals](#-high-fidelity-signals)
3. [Design Guardrails](#-design-guardrails)

---

## 🔍 Successful Outcomes

As a user, I want:

### 1. Portability & Isolation
* **Standalone Execution**: The `/serverinstaller` directory can be copied to any repo and execute correctly without external dependencies.
* **Environment Integrity**: The installer bootstraps from the host's existing tools and create isolated environments (e.g., `.venv`) to prevent leaks.
* **Zero-Touch Replication**: A real agent can execute `install.py --headless` and achieve a functional stack without human intervention.

### 2. Intelligent Discovery
* **Inventory Awareness**: The installer identifies all available components (Python, Node, Docker) and allows selective installation to prevent "package bloat."
* **Local Source Parity**: The tool installs the application *exactly as it exists* in the local root, respecting custom modifications.

### 3. Trust & Transparency
* **Surgical Integrity**: The `uninstall` command surgically reverses only the changes it made, ensuring the host is returned to its pre-installation state.
* **Before/After Verification**: Clear reports allow the operator (human or agent) to verify every change. No stealth modifications to PATH or Registry.

---

## 🚥 High-Fidelity Signals

* **Success**: `.librarian/manifest.json` correctly lists all artifacts, and `verify.py` reports `[VERIFIED]` for all items.
* **Failure**: Encountering an interactive prompt in `--headless` mode.
* **Success**: Running `uninstall.py` removes the `# Shesha Block` from `.zshrc` without deleting other aliases.

---

## 🛡 Design Guardrails

* **No Sudo**: Reject any feature that requires global `sudo` permissions if a local `.venv` alternative exists.
* **No Unmanaged Overwrites**: Reject any "auto-update" feature that replaces local configuration without a manifest-backed snapshot.
* **Respect Local Code**: Treatment of the current repository state as the "source of truth." Never overwrite local changes with upstream templates.
