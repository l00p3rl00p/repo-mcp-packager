# User Outcomes - Shesha Clean Room Installer

Success criteria for the portable clean room installer.

---

## ⚡ Quick Summary
* **Mission**: To provide a "Just Works" installation experience that creates zero-leak, isolated environments.

---

## 🔍 Successful Outcomes

As a user, I want:

### 1. Portability & Isolation
* **Standalone Execution**: The `/serverinstaller` directory can be copied to any repo and execute correctly.
* **Zero-Touch Replication**: Agents can execute `install.py --headless` without human intervention.

### 2. Intelligent Discovery
* **Inventory Awareness**: Identifies components automatically and allows selective installation.
* **Local Source Parity**: respetcs custom modifications in the local root.

### 3. Trust
* **Surgical Integrity**: Reverses changes accurately with `uninstall.py`.

---

## 🚥 High-Fidelity Signals
* **Success**: `.librarian/manifest.json` correctly list all artifacts.
* **Success**: `uninstall.py` removes the `# Shesha Block` markers.

---

## 🛡 Design Guardrails
* **No Sudo**: Reject features requiring global `sudo` if a local alternative exists.
* **Respect Local Code**: Never overwrite local experimental code with upstream templates.
