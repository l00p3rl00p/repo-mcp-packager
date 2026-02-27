# MCP Workforce Nexus: The Activator (repo-mcp-packager)

**The primary engine for deploying, hardening, and unifying MCP server environments with industrial-grade reliability.**

The **Activator** orchestrates the Workforce Nexus, transforming raw GitHub repositories into production-ready AI tools. It handles environment isolation, structural auditing, and atomic deployments.

## 🚀 True Start (Recommended)

To deploy and launch the **entire Workforce Nexus suite** (all 4 modules) via the master entry point:
```bash
../nexus.sh
```

**What this does:**
1.  **Verification**: Checks system health and security flags.
2.  **Launching**: Starts the system tray app and opens your browser.
3.  **Desktop**: Ensures "Start Nexus.command" is on your Desktop.

> **Universal Workspace**: For the high-level overview of the full ecosystem, see the [Master README](../README.md).

---

## 🏗️ Core Responsibilities (Orchestrator)

*   **Managed Isolation**: Creates and maintains the shared Nexus environment in `~/.mcp-tools`.
*   **Atomic Sync**: Synchronizes all 4 Nexus modules using the industrial convergence model.
*   **Safety Mandate**: Enforces the `set -o noclobber` safety standard across the suite.
*   **Desktop Launcher**: Injects absolute project paths into the macOS `.command` and Windows `.bat` launchers during setup.

---

## 🛠️ Global Command Reference

| Tool | Component | CLI | Responsibility |
| :--- | :--- | :--- | :--- |
| **Activator** | `repo-mcp-packager` | `./nexus.sh` | Orchestration, Integration, Sync |
| **Observer** | `mcp-server-manager` | `mcp-observer` | UI/GUI, Health, Inventory |
| **Surgeon** | `mcp-injector` | `mcp-surgeon` | Injection, Config Hardening |
| **Librarian** | `mcp-link-library` | `mcp-librarian` | Knowledge/ATP Sandbox |

---

## 🔐 Universal Safety & Rollback

Every operation follows a strict **Pre-flight -> Track -> Commit/Rollback** pattern.
1.  **Pre-flight**: Verifies host environment (Python version, write permissions).
2.  **Action**: Atomic installation/update with backup.
3.  **Audit**: Post-install verification via `nexus-verify.py`.

---

## 🔄 Drift Lifecycle Integration (v3.3.6+)

The Activator (Packager) integrates with the Drift Lifecycle system:
- **Sync Engine**: Manages repository state alignment during drift detection
- **Multi-Repo Orchestration**: Coordinates drift detection across all 4 Nexus repos
- **Safe Repair**: Deterministic repair without data loss

See main repo: [Drift Lifecycle System](../DRIFT_LIFECYCLE_OUTCOMES.md)

---

## 📝 Metadata
* **Status**: Production Ready (v3.3.6)
* **Part of**: The Workforce Nexus Suite
* **Protocol**: True Start v3.3.6
