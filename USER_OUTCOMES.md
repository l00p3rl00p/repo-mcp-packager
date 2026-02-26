# User Outcomes - Nexus Activator Packager (repo-mcp-packager)

This document defines success for the **Nexus Activator (The Forge)Packager**, the core engine responsible for deterministic installation, environment orchestration, and suite-wide synchronization.

---

## 🔗 Canonical Outcomes & Mission (Project Scope)

This repo-level `USER_OUTCOMES.md` is subordinate to the canonical [Workforce Nexus Mission Statement](/Users/almowplay/Developer/Github/mcp-creater-manager/USER_OUTCOMES.md).

## Core Mission Statement - READ ONLY- NEVER EDIT

The mission is to achieve 100% deterministic installation and suite-wide synchronization through an autonomous 'Just Works' orchestration engine. By maintaining a hardened Managed Mirror and providing atomic, surgical updates, it ensures the entire Workforce Nexus suite remains stable, isolated, and perfectly aligned with its source of truth across any host system.

### The Rule of Ones: The ACTIVATOR PACKAGER (The forge)System Architecture 
The Nexus Activator provides the structural foundation and update loop for the ecosystem, anchored in:
- **One Install Path:** A single, unified deployment script (`setup.sh` / `nexus.sh`) that bootstraps the entire suite.
- **One Entry Point:** The `mcp-activator` CLI and the "Maintenance" section of the Nexus Commander GUI.
- **One Status:** Deterministic verification reports (`verify.py`) proving suite-wide alignment and environment health.
- **One Log:** Detailed logs of repository synchronization, virtual environment creation, and dependency resolution.



---

## 📋 Table of Contents
1. [Successful Outcomes](#-successful-outcomes)
2. [High-Fidelity Signals](#-high-fidelity-signals)
3. [Design Guardrails](#-design-guardrails)

---

## 🔍 Successful Outcomes (Nexus Activator)

As a user, I want:

### 1. Deterministic Suite Installation
* **One-Command Setup**: Run `./nexus.sh` from any project root to automatically pull the suite, build the environments, and launch the dashboard.
* **Environment Integrity**: Bootstraps isolated virtual environments (`.venv`) for all components to prevent global package leaks and version conflicts.
* **Zero-Touch Replication**: A real agent or non-technical user can execute the installer in headless mode and achieve a 100% functional stack without intervention.

### 2. Intelligent Syncing (Managed Mirror)
* **Autonomous Bootstrap**: Fetch the entire Workforce Nexus suite from GitHub even if only a single standalone script is present locally.
* **Industrial Repair**: Running `mcp-activator --repair` triggers the full rebuild loop: source sync + venv + GUI rebuild.
* **Inventory Awareness**: Automatically identify available developer tools (Python, Node, Docker) and tailor the installation to the host's capabilities.

### 3. Trust & Surgical Reversibility
* **Clean Uninstall**: The `uninstall.py` command must surgically reverse ONLY the changes it made, returning the host system to its pre-installation state (removing PATH blocks, wrappers, and central tool dirs).
* **Before/After Verification**: Generate a detailed "Purge Checklist" on the OS Desktop after uninstallation to prove removal of all artifacts.

### 4. Resilient Lifecycle
* **Context-Locked Execution**: Entry points (`mcp-*`) must carry their own venv pointers to work regardless of the user's active terminal or global Python state.
* **Atomic Rollback**: If an installation or sync step fails, the Activator must revert to the last known-good state to avoid leaving broken partial artifacts.

### 2. Intelligent Discovery & Autonomy
* **Autonomous Bootstrap**: The Activator can fetch the entire Workforce Nexus suite from GitHub, allowing it to move from "standalone script" to "suite architect" without local source siblings.
* **Inventory Awareness**: The installer identifies all available components (Python, Node, Docker) and allows selective installation to prevent "package bloat."
* **Local Source Parity**: In developer mode, the tool installs the application *exactly as it exists* in the local root, respecting custom modifications.

### 3. Trust & Transparency
* **Surgical Integrity**: The `uninstall` command surgically reverses only the changes it made, ensuring the host is returned to its pre-installation state.
* **Before/After Verification**: Clear reports allow the operator (human or agent) to verify every change. No stealth modifications to PATH or Registry.

### 4. Universal Observability
* **Visual Status**: The user can see the health and connection status of all Nexus components (Observer, Librarian, Injector, Activator) in a single dashboard.
* **Graceful Degradation**: The system functions even if components are missing, clearly indicating what is available vs. what needs installation.

### 5. Resilient Lifecycle
* **Atomic Rollback**: If an installation fails at any step, the system automatically reverts to a clean state, leaving no partial artifacts.
* **Safe Upgrades**: The `mcp-activator --repair` command is the single unified update loop — pulls source, rebuilds venv, rebuilds GUI.
* **Context-Locked Execution**: Entry points carry their own venv and PYTHONPATH, ensuring they work regardless of the user's active terminal environment.

---

## 🚀 Roadmap to 100% Compliance

To fully align with these outcomes, the following enhancements are planned:

*   **GUI Reliability (Target 95%+)**: Transition GUI from a blocking process to a background service with PID management.
*   **Librarian Synergy**: Implement a dynamic watcher so the Librarian indexes changes in real-time, not just on installation.
*   **Operational Awareness**: Add "version health" checks to the GUI dashboard to visually signal when a `--repair` is required.

### 2026-02-11 Alignment Update
* **Injector Startup Detect**: Added startup detection/prompt flow for common IDE clients, including `claude`, `codex`, and `aistudio` (plus `google-antigravity` alias).
* **Package-Created Component Injection Policy**: If full Nexus components are detected (`~/.mcp-tools/bin`), the injector prompts injection only for components that are **actual MCP servers over stdio** (currently `nexus-librarian`). Other Nexus binaries (e.g. `mcp-activator`, `mcp-observer`) are CLIs and should not be injected into MCP clients.
* **Tier-Aware GUI Control Surface**: GUI command widgets now map to command catalog behavior with visual unchecked state for unsupported tier actions.
* **Web-Client Proxy Best Practice**: For browser-based AI clients, the recommended pattern is to run a local MCP proxy that exposes SSE / Streamable HTTP / WebSocket endpoints (CORS + health) and connect the web client to that proxy.
* **GUI Daemon Management (PID + Logs)**: The GUI supports daemon-mode widgets for long-running services (start returns a PID + log file; stop + log tail are available via the GUI API).
* **Central-Only Uninstall Policy**: Full wipes only touch approved central locations (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block). No disk scans or directory-tree climbing during uninstall.
* **Uninstall Safety + Diagnostics**: Uninstall now prints an explicit deletion plan and requires confirmation (unless `--yes`). Added `--verbose` and `--devlog` (JSONL) with 90-day retention for diagnostics.
* **Bootstrap Safety Policy**: Workspace detection avoids filesystem crawling (checks only `cwd` + script-sibling workspace). If a workspace `.env` is present, the installer warns about potential conflicts with the central install.

---

## 🚥 High-Fidelity Signals

* **Success**: `.librarian/manifest.json` correctly lists all artifacts, and `verify.py` reports `[VERIFIED]` for all items.
* **Failure**: Encountering an interactive prompt in `--headless` mode.
* **Success**: Running `uninstall.py` removes the `# Nexus Block` from `.zshrc` without deleting other aliases (legacy installs may still contain `# Shesha Block`).

---

## 🛡 Design Guardrails

* **No Sudo**: Reject any feature that requires global `sudo` permissions if a local `.venv` alternative exists.
* **No Unmanaged Overwrites**: Reject any "auto-update" feature that replaces local configuration without a manifest-backed snapshot.

---
### 2026-02-25 Command Unification Update (v3.3.4)
* **`--repair` is now the single command**: Replaced the dual `--sync` / surgical `--repair` with one unified `--repair` flag that does everything — source copy, venv rebuild, GUI rebuild, Librarian index.
* **Auto GUI Rebuild**: `build_gui_if_stale()` runs inside `--repair`. No separate `npm run build` step needed.
* **`py-modules` Fix**: `nexus_devlog` and `nexus_session_logger` are now declared in `pyproject.toml`, eliminating the `ModuleNotFoundError` on first run.

---
### 2026-02-25 Mission Audit Results (v3.3.4 Red Team)
**Mission Score: 89%** | Anchored to: *"100% deterministic installation and suite-wide synchronization."*

| Feature | Status | Confidence |
|---|---|---|
| Deterministic install (`./nexus.sh` → full stack) | ✅ | 95% |
| Managed Mirror (`--repair` = source sync + reset) | ✅ | 90% |
| Atomic rollback on failure | 🟡 | 70% |
| Auto GUI rebuild on `--repair` | ✅ | 92% |
| Verification reports (`nexus-verify.py` exits 0) | ✅ | 95% |
| One Entry Point: `mcp-activator --repair` | ✅ | 99% |
| venv creation + dependency resolution logged | ✅ | 85% |

#### 🔴 GAP-R1 (Open — v48 Backlog)
> **Claim**: Atomic rollback if install fails at any step.
> **Gap**: No ORT evidence that a mid-flight `--repair` failure (disk full, network drop) triggers a clean rollback. This is unproven ghost code until an ORT verifies it.
> **Fix**: Write an ORT that intentionally interrupts `--repair` mid-git-pull and confirms the host is left clean.

---
*Status: v3.3.4 Audited — 2026-02-25*
