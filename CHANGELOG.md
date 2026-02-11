# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Central-only uninstall upgrades:
  - `--verbose` and `--devlog` (JSONL) with 90-day retention pruning.
  - `--dry-run` to print the deletion plan without making changes.
  - Explicit deletion plan + confirmation prompt (unless `--yes`).
- Per-repo suite installation support (no disk scanning):
  - Forwarder `bootstrap.py` in single repos supports `--install-suite` to clone missing components into `~/.mcp-tools`.
- Devlog capture for bootstrap subprocesses (git/pip/indexing/injection prompts).
- Added E2E HTTP GUI test (ephemeral port) to validate `/api/*` endpoints and action log creation.
- Added PATH block removal tests for `.zshrc` and `.bashrc`.
- Standardized all documentation (.md) across the workspace using the `MD_FORMAT.md` reference.
- Added proper Table of Contents and Quick Starts to all README files.
- Consolidated User Outcome mission statements into dedicated files.
- Added injector startup auto-detection and prompt flow (`--startup-detect`) for common MCP-capable IDE clients.
- Added package-component-aware injection prompting for Nexus-created binaries (limited to MCP-server components such as `nexus-librarian`).
- Added support alias `google-antigravity` for AI Studio client path selection.
- Added tier-aware GUI command control surface scaffolding with full `COMMANDS.md` widget mapping.

### Fixed
- GUI action execution no longer fails when logs directory is not writable (uses resolved writable logs dir).
- GUI “Update Tools” now routes through Activator suite sync (`bootstrap.py --sync`) instead of a missing script.
- Fixed `serverinstaller/install.py` syntax/control-flow issue in `run()` that previously prevented execution.
- Improved injector permission error handling for unwritable client config parent directories.

---

## [0.5.0] - 2026-02-09

### Added
- **Portable Installer**: Moved installation logic to a standalone `/serverinstaller` directory for easy replication.
- **Headless Mode**: Added `--headless` flag to bypass all interactive prompts and TTY requirements.
- **NPM Policy**: Added `--npm-policy` for selective Node/NPM isolation (local vs global).
- **Surgical Reversal**: Implemented marker-aware shell configuration cleanup in `uninstall.py`.
- **Dynamic Discovery**: Installer now respects "Install-as-is" logic for local source parity.
- **Component Inventory**: Added interactive selection and `--no-gui` flags for selective installation.

### Changed
- **Legacy Compatibility**: Hardened installer logic to support Python 3.9+ for the bootstrap wavefront.

### Fixed
- **Manifest Tracking**: Fixed manifest generation to accurately track all created artifacts for clean removal.
