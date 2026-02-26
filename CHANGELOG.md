# Changelog - Nexus Activator (repo-mcp-packager)

## [3.3.3] - 2026-02-20

### Changed
- **Suite Version Sync**: Aligned component and docs to Nexus `v3.3.3`.

## [3.2.1] - 2026-02-19

### Improvements
- **True Start**: Component-aware interactive onboarding now included in `./setup.sh`.
- **Suite Sync**: Version alignment with Nexus v3.2.1.

### Fixed
- **`install.py`**: Fixed syntax error (escaped quotes) in `GLOBAL_CONFIG_KEY`.

### Security
- `gui_bridge.py` CORS restricted to `localhost` origins only — wildcard removed.
- 4× bare `except:` blocks replaced with typed handlers (`json.JSONDecodeError`, `sqlite3.OperationalError`, `OSError`).
- `forge_engine.py`: `os.popen("date")` → `datetime.utcnow()` (eliminates shell subprocess for timestamps).

---

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
*Status: Production Ready (v3.3.3)*
