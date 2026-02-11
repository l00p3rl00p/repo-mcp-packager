# Workforce Nexus: Commands (Quick Start)

This file is the **human-first** quick command sheet.

For the exhaustive, verifiable command matrix, see `COMMANDS.md`.

---

## Install / Update (Activator)

Run from this repo (recommended):

```bash
python3 bootstrap.py --permanent
```

Update/sync an existing central install:

```bash
python3 bootstrap.py --sync
```

Launch the GUI after install:

```bash
python3 bootstrap.py --gui
```

---

## GUI (Observer)

```bash
python3 -m mcp_inventory.cli gui
```

Default URL: `http://localhost:8501`

---

## IDE Injection (Surgeon)

List supported IDE clients:

```bash
python3 ../mcp-injector/mcp_injector.py --list-clients
```

Guided injection (recommended):

```bash
python3 ../mcp-injector/mcp_injector.py --startup-detect
```

---

## Uninstall (Central-Only, Safe by Default)

This uninstaller **only touches approved central locations** (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block).
It does **not** scan your disk or delete anything in your git workspace.

Full wipe (includes Nexus environments under `~/.mcp-tools/.venv`):

```bash
python3 uninstall.py --purge-data --kill-venv
```

Diagnostics:

```bash
python3 uninstall.py --purge-data --kill-venv --verbose --devlog
```

Notes:
- If you want to preserve environments, omit `--kill-venv`.
- `--devlog` writes JSONL devlogs under `~/.mcpinv/devlogs` with 90-day retention.

