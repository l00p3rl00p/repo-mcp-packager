# Changelog - Nexus Activator (repo-mcp-packager)

## [2.0.0] - 2026-02-18

### 🚀 Adaptive Lifecycle
- **Sync & Repair**: Introduced `--sync` for workspace alignment and `--repair` for automated binary restoration.
- **Noclobber Mandate**: Hardened shell environment to enforce `set -o noclobber` safety standard.
- **Industrial Uninstaller**: Enhanced surgical cleanup with explicit deletion plans and backup-before-write logic.

### 🛡️ Safety & Stewardship
- **Shell Safe List**: Implemented execution tiers (Green, Yellow, Black) to protect the host environment.
- **Detached GUI Process**: GUI now launches as a background service with robust PID management in `~/.mcpinv/runtime.json`.

### Fixed
- **Venv Resilience**: Improved shared venv creation and permission handling in `~/.mcp-tools`.

---

## [0.5.0] - 2026-02-09
- Portable Installer logic.
- Headless replication mode.
- Industrial path management (`~/.mcp-tools`).

---
*Status: Production Ready (v2.0.0)*
