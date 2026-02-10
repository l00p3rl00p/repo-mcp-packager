# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Standardized all documentation (.md) across the workspace using the `MD_FORMAT.md` reference.
- Added proper Table of Contents and Quick Starts to all README files.
- Consolidated User Outcome mission statements into dedicated files.

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
