# Environment: Clean Room Setup

Technical environment requirements and audit logic for the Shesha Clean Room Installer.

## Core Dependency Rules

### 1. Python Compatibility
- **Installer Wavefront**: The installer scripts (`install.py`, `audit.py`, etc.) are hardened for **Python 3.9+**. This ensures that the bootstrap process itself is robust across legacy environments.
- **Application Engine**: The core Shesha RLM / MCP stack typically requires **Python 3.11+**. The installer checks this during the audit and will issue a warning if the host environment is too old for the engine.

### 2. Node.js & NPM
- **Requirement**: Only required if installing the `GUI Frontend`.
- **Policy**: Supports `--npm-policy local` (isolated) or `global` (host).

### 3. Docker
- **Requirement**: Required for RLM sandbox features and Dockerized query tracing.
- **Access**: The installer verifies `docker info` to ensure the daemon is accessible.

## Environment Audit Logic

### Pre-flight Probe
1.  **Shell Detection**: Captures active shell type and RC paths (`.zshrc`, `.bashrc`).
2.  **Binary Discovery**: Locates `npm`, `node`, `docker`, and `pip`.
3.  **Component Inventory**: Scans the root workspace to identify available installation targets.

## Configuration Policies

### NPM Isolation (`--npm-policy`)
- `local`: Installs private binaries. Recommended for production wavefronts to prevent environment leak.
- `global`: Uses system `npm`.

### Docker Enforcement (`--docker-policy`)
- `fail`: Hard abort if Docker is inaccessible.
- `skip`: Proceed but disable sandbox-dependent features.

## Standalone Tools

### MCP JSON Injector
**Purpose**: Manual MCP server configuration without breaking JSON syntax.

**Requirements**:
- Python 3.6+ (no external dependencies)
- Write access to IDE config directories

**Use Case**: When the main installer's auto-attachment isn't available or you need granular control over individual IDE configurations.
