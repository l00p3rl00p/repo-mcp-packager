# Environment - Git Repo MCP Converter & Installer

Technical environment requirements and audit logic for the portable clean room installer.

---

## 📋 Table of Contents
1. [Core Dependency Rules](#-core-dependency-rules)
2. [Environment Audit Logic](#-environment-audit-logic)
3. [Configuration Policies](#-configuration-policies)
4. [Standalone Utility Requirements](#-standalone-utility-requirements)

---

## 🔍 Core Dependency Rules

### 1. Python Compatibility
* **Installer Wavefront**: The installer scripts (`install.py`, `audit.py`, etc.) are hardened for **Python 3.9+**. This ensures the bootstrap process itself is robust across legacy environments.
* **Application Engine**: The core stack typically requires **Python 3.11+**. The installer checks this during audit and issues a warning if the host environment is too old.

### 2. Node.js & NPM
* **Requirement**: Only required if installing the GUI Frontend.
* **Policy**: Supports `--npm-policy local` (isolated) or `global` (host).

### 3. Docker
* **Requirement**: Required for RLM sandbox features and Dockerized query tracing.
* **Access**: The installer verifies `docker info` to ensure daemon accessibility.

---

## 🛠 Environment Audit Logic

### Pre-flight Probe
1. **Shell Detection**: Captures active shell type and RC paths (`.zshrc`, `.bashrc`).
2. **Binary Discovery**: Locates `npm`, `node`, `docker`, and `pip`.
3. **Component Inventory**: Scans the root workspace to identify available installation targets.

---

## ⚙️ Configuration Policies

### NPM Isolation (`--npm-policy`)
* **`local`**: Installs private binaries. Recommended for production wavefronts to prevent environment leak.
* **`global`**: Uses system `npm`.

### Docker Enforcement (`--docker-policy`)
* **`fail`**: Hard abort if Docker is inaccessible.
* **`skip`**: Proceed but disable sandbox-dependent features.

---

## 🛠 Standalone Utility Requirements

### MCP JSON Injector
* **Requirement**: Python 3.6+ (no external dependencies).
* **Access**: Write access to IDE config directories.
* **Use Case**: Manual configuration or granular control over individual IDE setups.
