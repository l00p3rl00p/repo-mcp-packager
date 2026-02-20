# Changelog

All notable changes to the Nexus Clean Room Installer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Standardized all documentation using `MD_FORMAT.md`.
- Clarified injector startup detect flow and multi-IDE prompting guidance in manual configuration docs.
- Uninstall diagnostics and safety:
  - `--verbose`, `--devlog` (JSONL) with 90-day retention pruning.
  - `--dry-run` to print deletion plan without making changes.
  - Explicit deletion plan + confirmation prompt (unless `--yes`).

### Fixed
- Repaired `install.py` control-flow/syntax path in `run()` to restore executable installer behavior.

## [0.5.0] - 2026-02-09

### Added
- **Portable Installer**: Standalone `/serverinstaller` directory.
- **Headless Mode**: Added `--headless` flag.
- **Surgical Reversal**: Marker-aware cleanup in `uninstall.py`.

### Fixed
- **Manifest Tracking**: Fixed accurately tracking created artifacts.
