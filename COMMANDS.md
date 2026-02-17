# Workforce Nexus: Exhaustive Command Reference

This document provides a complete list of commands for all modules in the Workforce Nexus suite.

Scope note: to avoid documentation drift, this table lists **only commands/flags that are verifiably present in this repo workspace** (i.e., `python3 … --help` shows them). Global wrappers (e.g. `mcp-activator`) may exist after installation, but their exact CLI surface depends on the installed shims.

---

## 🚀 The Activator (repo-mcp-packager)
**Main Responsibility**: Orchestration, Multi-tool Installation, and Workspace Sync.

| Command | Expected outcome |
| :--- | :--- |
| `python3 bootstrap.py --permanent` *(alias: --industrial)* | Installs/syncs the full Nexus suite into `~/.mcp-tools` and hardens wrappers. |
| `python3 bootstrap.py --lite` | Performs a lite (zero-dep) install path (no shared venv). |
| `python3 bootstrap.py --sync` *(alias: --update)* | Updates the central install from local workspace (if available) or GitHub. |
| `python3 bootstrap.py --gui` | Launches the GUI after install/sync. |
| `python3 serverinstaller/install.py` | Packages a single repo (standalone installer flow). |
| `python3 uninstall.py --kill-venv --purge-data` | Removes only approved central artifacts (no disk scan). |
| `python3 gui/server.py --port 8787` | Runs the Nexus Control Surface (HTTP) on localhost. |

---

## 👁️ The Observer (mcp-server-manager)
**Main Responsibility**: Real-time observability, health monitoring, and the Visual Dashboard.

| Command | Expected outcome |
| :--- | :--- |
| `mcp-observer gui` | Opens the local Observer GUI dashboard. |
| `mcp-observer scan .` | Scans for MCP candidates and updates inventory (confirmed-only auto-add). |
| `mcp-observer list` | Prints the current inventory list. |
| `mcp-observer check-synergy` | Checks suite integration assumptions and reports status. |
| `mcp-observer running` | Shows runtime observations (docker + mcp-ish processes). |

---

## 💉 The Surgeon (mcp-injector)
**Main Responsibility**: Precise JSON configuration injection for IDEs (Claude, Cursor, etc.).

| Command | Expected outcome |
| :--- | :--- |
| `mcp-surgeon --startup-detect` | Detects installed clients, then lets you inject suite servers / custom servers / removals via numbered prompts (TTY-only). |
| `mcp-surgeon --client claude --add` | Adds a server entry to Claude’s config (interactive). |
| `mcp-surgeon --client claude --remove <name>` | Removes one server entry by name from Claude’s config. |
| `mcp-surgeon --client claude --list` | Lists server entries in Claude’s config. |
| `mcp-surgeon --list-clients` | Shows known client config locations and which exist on disk. |

*Supported Clients: `claude`, `cursor`, `vscode`, `xcode`, `codex`, `aistudio`, `google-antigravity` (alias of AI Studio)*

### Injection modes (important)
There are two different workflows, and they behave differently:

1) **Detected injection** (`--startup-detect`)
* Purpose: auto-detect *clients* (Codex/Claude/etc.) and offer injection for *suite-known* MCP stdio servers (currently `nexus-librarian`).
* Notes:
  * This prompt is **TTY-only**. If stdin is not interactive (GUI runners/agents), it will skip prompting.
  * This does **not** let you redefine the injected command; it uses detected components when available.

2) **Custom injection** (`--add`)
* Purpose: you define the server entry explicitly (**name + command + args + env**) and the injector writes it safely into the selected client config.
* Use this when you want to inject **any** MCP stdio server (not just the suite-known defaults).

### Suite stdio server (what to inject)
Only inject tools that speak MCP over **stdio** (JSON-RPC on stdout). In this suite, the injectable stdio server is:
* `nexus-librarian` → command `mcp-librarian` with args `--server`

Concrete examples (global install):
* List Codex config servers: `mcp-surgeon --client codex --list`
* Inject the suite server into Codex (interactive): `mcp-surgeon --client codex --add`
* Remove it: `mcp-surgeon --client codex --remove nexus-librarian`

Avoid injecting these CLIs as MCP servers (they are not stdio MCP servers):
* `mcp-activator`, `mcp-observer`, `mcp-surgeon`

---

## 📚 The Librarian (mcp-link-library)
**Main Responsibility**: Knowledge persistence, link storage, and local codebase indexing.

| Command | Expected outcome |
| :--- | :--- |
| `mcp-librarian --add <url>` | Adds a URL to the local link library. |
| `mcp-librarian --list` | Lists active links. |
| `mcp-librarian --search <query>` | Searches stored links. |
| `mcp-librarian --index <dir>` | Indexes a local directory. |
| `mcp-librarian --index-suite` | Indexes suite data (Observer/Injector). |
| `mcp-librarian --server` | Runs as a stdio MCP server (injectable into clients). |

---

## 🌍 Directory Context Rules

### 1. Where to run what?
*   **Autonomous Bootstrap**: Run `python3 bootstrap.py --permanent` from a standalone copy of the bootstrapper. It will automatically fetch the rest of the Workforce Nexus suite from GitHub if sibling repositories are not found.
*   **Installation/Dev Mode**: Run from the root of a full workspace.
*   **Daily Global Use**: Once installed, run `mcp-surgeon`, `mcp-observer`, etc., from **any directory** in your terminal.
*   **Standalone Installer**: Run `python3 serverinstaller/install.py` from the root of the repository you wish to package.

### 2. Service Management
*   **Starting GUI**: `mcp-observer gui`
*   **Stopping GUI**: Press `Ctrl + C` in the terminal where it's running.
*   **Restarting**: Just rerun the command. It will automatically re-index your active servers.

### 3. PATH Setup
By default, Industrial installs place short-command wrappers in `~/.local/bin`.

If `mcp-` commands are not found, first add this to your `~/.zshrc` (macOS) or `~/.bashrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Optional (opt-in): you can also add the Nexus central bin directory:
```bash
export PATH="$HOME/.mcp-tools/bin:$PATH"
```

---

## 🧩 GUI Widget Coverage

The Nexus GUI scaffold in `repo-mcp-packager/gui/` now maps **every executable command** in this `COMMANDS.md` table to a widget action.

* Widgets are **tier-gated** (`lite`, `standard`, `permanent`): unsupported actions render visually unchecked.
* Widget execution routes through a safe backend allowlist (`widget_id`-based), then reports stdout/stderr and exit code.
* Scope model is preserved: each repo remains standalone, while suite commands still assemble the integrated package.

In addition, the GUI may include a small number of **external helper workflows** (for example, `npx`-based MCP proxies) that are not part of the Nexus repos themselves.
