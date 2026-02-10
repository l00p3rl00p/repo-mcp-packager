# Architecture: Portable Clean Room Installer

Technical Truth and Developer Workflow for the Shesha Clean Room Installer.

## Tactile Workflow

### Installation (Guided)
```bash
python serverinstaller/install.py
```
*Triggers interactive inventory probes, offers elective component selection, and PATH setup.*

### Installation (Headless)
```bash
python serverinstaller/install.py --headless --no-gui
```
*Zero-touch replication. Optionally skip GUI using `--no-gui` for minimalist CLI-only nodes.*

### Verification
```bash
python serverinstaller/verify.py
```
*Generates Before/After transformation report based on audit snapshot.*

### Cleanup/Uninstall
```bash
python serverinstaller/uninstall.py --kill-venv
```
*Marker-aware surgical reversal and artifact removal.*

## Logic Model & Subsystems

### 1. Probe Layer (`audit.py`)
- **System Sniffing**: Non-destructive detection of Shell, Node, NPM, Docker, and Python environments.
- **Portability Hardening**: Logic is designed to run on Python 3.9+ to ensure the installer works on older systems, even if the primary application requires 3.11+.

### 2. Execution Layer (`install.py`)
- **Discovery**: Scans parent directory (`../`) for specific indicators (`pyproject.toml`, `package.json`).
- **Inventory Awareness**: Presents a list of discovered components. In guided mode, the user can selectively toggle installation.
- **Enforcement**: Bootstraps the `.venv` and installs dependencies based on selection.
- **Instrumentation**: Wraps shell PATH updates in `# Shesha Block` markers for guaranteed safe reversal.

### 3. State Management (`manifest.json`)
- **Registry**: Logs every file, directory, or shell configuration change.
- **Integrity**: Essential for `uninstall.py` to achieve zero file-leak cleanup.

### 4. Standalone Utilities

#### MCP JSON Injector (`/mcp_injector.py`)
- **Purpose**: Safely add/remove MCP server entries from IDE config files.
- **Zero Dependencies**: Pure Python stdlib, no external packages.
- **Surgical JSON**: Handles bracket/comma logic automatically.
- **Portable**: Lives at repo root, completely independent of serverinstaller.
- **Installation**: `./mcp_injector_install.sh` or use directly.

### 5. MCP Bridge Generator (`bridge.py`)

- **Purpose**: Wrap legacy automation code as MCP servers.
- **Discovery**: Scans Python scripts for `if __name__ == "__main__"` blocks.
- **Code Generation**: Creates `mcp_server.py` that exposes legacy functions as MCP tools.
- **Soft Dependency**: Optionally uses `/mcp_injector.py` for auto-attachment to IDEs.
- **Graceful Fallback**: Works standalone by printing manual configuration instructions.

## Constraints & Security

- **Local-Only**: Bootstraps from the local repository state only. No remote template fetching.
- **Permissions**: Guided mode explicitly asks for permission before modifying any host RC files.
- **Self-Documenting**: Failures in subprocesses (like `pip`) are captured and logged as warnings rather than hard crashes, ensuring the installer completes its audit output.

## Universal Bootstrap & Mutual Discovery

### Philosophy

Each Git-Packager repository can act as a complete workspace installer. This "entry point agnostic" design means:
- Users can clone any single repo and bootstrap the full workspace from there
- Each tool remains 100% functional standalone
- Integration is opt-in via explicit user consent

### Resolution Strategy

The `bootstrap.py` module implements a three-tier resolution:

1. **Local**: Check if component exists in current project root
2. **Sibling**: Check workspace parent directory for sibling repos
3. **Remote**: Offer to `git clone` from GitHub if missing

### Integration Points

- **mcp-injector**: `python mcp_injector.py --bootstrap`
- **mcp-server-manager**: `mcpinv bootstrap`
- **repo-mcp-packager**: `python bootstrap.py` (native)

All three entry points run the same universal bootstrapper logic.
