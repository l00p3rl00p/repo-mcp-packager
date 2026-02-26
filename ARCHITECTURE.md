# Architecture - Workforce Nexus Activator (repo-mcp-packager)

**The technical blueprint for the Nexus Lifecycle Orchestrator.**

The **Activator** is the "General Contractor" of the Workforce Nexus. It moves from raw repository assets to a production-ready suite by managing environment isolation, industrial sync, and cross-platform launcher injection.

---

## 🔍 Core Philosophy: The Clean Room Installer

The Activator follows the **Clean Room** principle. It treats every repository as an isolated environment and ensures that:
1.  **Zero-Dep Bootstrap**: The core installer requires only the Python Standard Library.
2.  **Volatile Isolation**: Dependencies are kept in the `~/.mcp-tools` shared environment.
3.  **Surgical Traceability**: Every bit flipped or file created is recorded in a manifest for atomic reversal.

---

## 🏗 Subsystem Breakdown

### 1. The Audit Layer (`audit.py` / `nexus-verify.py`)
Discovery logic that detects Shell type (bash/zsh), Python metadata, and workspace health.
* **Q1 Trigger**: `nexus-verify.py` acts as the definitive success/failure probe for the entire suite.
* **Capabilities**: Detects GitHub vs Local context and recommends the optimal installation tier.

### 2. The Execution Engine (`install.py` / `bootstrap.py`)
Orchestrates the transition from raw code to a managed service.
* **Structural Audit**: Scans for `pyproject.toml`, `package.json`, and `.git` markers.
* **Reliability Tiers**:
    - **Lite**: Loose binding, zero-dep wrappers.
    - **Standard**: Cohesive linked-workspace integration.
    - **Industrial (Unified)**: Hardened, single-venv production environment.

### 3. Lifecycle Management (`nexus.sh` / `setup.sh`)
Provides the **True Start Protocol**.
* **Interactivity**: `setup.sh` handles dependency resolution (Node, Python libraries).
* **Launcher Injection**: Dynamically writes absolute paths into macOS `.command` and Windows `.bat` launchers to ensure portability from the Desktop.

### 4. Registry & State
Managed via `manifest.json` and the shared `.mcpinv` directory.
* **Atomic Tracking**: Every artifact is tracked for clean uninstallation.
* **Versioning**: Enforces suite-wide version synchronization (currently v3.3.3).

---

## 🔐 Universal Safety Protocol (USP)

### Phase 1: Pre-flight
- **Write Test**: Verifies permissions in `~/.mcp-tools`.
- **Space Check**: Verifies storage health.

### Phase 2: Atomic Tracking
Every command adds to a rollback journal.

### Phase 3: Commit or Rollback
- **Success**: Manifest is locked, and `nexus-verify.py` is triggered.
- **Failure**: Automatic reversal of all partial installations.

---

## 📝 Metadata
* **Status**: Production Ready (v3.3.3)
* **Author**: l00p3rl00p
* **Part of**: The Workforce Nexus Suite
