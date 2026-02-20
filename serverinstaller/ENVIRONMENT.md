# ENVIRONMENT.md — Nexus Clean Room Installer (serverinstaller)

Environment expectations and safety boundaries for the **canonical installer/uninstaller** shipped by the Nexus suite.

---

## 🔍 Core Dependency Rules

### Python
* **Minimum**: Python **3.9+**
* **Recommended**: Python **3.11+**

### Node / Docker
* Optional. Only required for features that explicitly require them.

---

## 🛠 Approved Central Locations (Hard Boundary)

The installer/uninstaller is **central-only** and will never do broad filesystem searches.

Approved locations include:
* `~/.mcp-tools` (suite home)
* `~/.mcpinv` (shared state + devlogs)
* Shell RC files for PATH block removal (e.g. `~/.zshrc`, `~/.bashrc`, `~/.bash_profile`)

If a user wants to remove a git workspace (where they ran the installer from), the tools will print **manual cleanup commands** instead of deleting workspace files.

---

## 🧾 Devlogs (Shared Diagnostics)

Shared JSONL devlogs live under:
* `~/.mcpinv/devlogs/nexus-YYYY-MM-DD.jsonl`

Behavior:
* Entries are appended as actions run.
* Old devlog files are pruned on use (90-day retention).
* `--devlog` enables additional capture for subprocess stdout/stderr (best-effort).

---

## 🧹 Uninstall Behavior (Previewable + Confirmable)

The canonical uninstaller supports:
* `--dry-run` to preview what would be removed
* `--verbose` for more detail
* `--devlog` to record uninstall actions to the shared devlog
* `--kill-venv` to remove the shared venv (kept by default)
* `--purge-data` to remove shared suite data under `~/.mcp-tools` / `~/.mcpinv`

It will:
* list the central deletion plan
* ask for confirmation (unless `--yes`)
* remove the Nexus PATH block markers safely (with backups)

---

## 📝 Metadata
* **Status**: Hardened
* **Reference**: [README.md](./README.md)
