# ENVIRONMENT.md — Workforce Nexus Suite (repo-mcp-packager)

Host environment requirements, safety rules, and OS-specific paths for the **Workforce Nexus** “Activator/Packager” repo.

---

## 🔍 Core Dependency Rules

### 1. Python Runtimes
* **Minimum**: Python **3.9+**.
* **Recommended**: Python **3.11+**.
* **Isolation**: The suite uses a **central venv** under the Nexus home (see paths below). It does **not** require (or create) a venv in your git workspace.

### 2. Node.js & NPM
* Optional (only if a repo’s GUI requires Node): Node.js **18+**.

### 3. Docker Ecosystem
* Optional (only for features that explicitly require Docker).

---

## 🛠 OS-Specific Path Matrix

The Workforce Nexus suite centralizes all artifacts in a predictable, user-owned location.

| Platform | Nexus Home Root | Notes |
| :--- | :--- | :--- |
| **macOS** | `~/.mcp-tools` | Shared suite home |
| **Linux** | `~/.mcp-tools` | Shared suite home |
| **Windows** | `%USERPROFILE%\.mcp-tools` | Shared suite home |

Additional Nexus suite paths (all are **central**):
* Tools bin: `~/.mcp-tools/bin`
* Shared venv (if created): `~/.mcp-tools/.venv`
* Shared state/devlogs: `~/.mcpinv/` (see Devlogs section)
* Global injector config (created on install if missing): `~/.mcp-tools/config.json`

---

## 🛠 Environment Audit Logic: The Pre-flight Probe

The `audit.py` module performs a multi-stage probe to build a system capabilities map.

### Stage 1: Shell Detection
The probe identifies the active shell via the `SHELL` environment variable.
* **Targets**: `.zshrc` (macOS default), `.bashrc`, `.bash_profile`.
* **Action**: Determines which RC file would receive (or remove) the Nexus PATH block **only when opt-in flags are used**.

### Stage 2: Binary Path Discovery
Uses `shutil.which` to find system binaries for:
* `python3`
* `git`
* (optional) `node`, `npm`, `docker`

### Stage 3: Feature Inventory
The suite avoids “walk up” scans. It only checks:
* the **current working directory** (your terminal `cwd`), and
* the directory **next to the running script** (script-sibling context),

…to decide whether you’re running inside a repo checkout and to warn about obvious workspace issues (like a local `.env`).

---

## ⚙️ Configuration Policies

### Central-Only Safety Policy (No Disk Scans)
To reduce risk and surprise:
* Uninstall operations only touch **approved central locations** (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block).
* Bootstraps and uninstallers do **not** crawl the filesystem or walk up directory trees to “find” workspaces.
* Workspace cleanup is **manual** by design: if a workspace might be affected, the tools print manual commands instead of deleting workspace files.

### Devlogs (Shared Diagnostics)
The suite supports shared JSONL devlogs under:
* `~/.mcpinv/devlogs/nexus-YYYY-MM-DD.jsonl`

Behavior:
* Entries are appended as actions run.
* Old devlog files are pruned on use (90-day retention).
* `bootstrap.py --devlog` captures stdout/stderr from key subprocesses (git/pip/indexing/injection prompts).

### PATH Management (Surgical Injection)
The bootstrap can optionally add the suite bin directory to the host PATH using unique markers to ensure safe uninstallation.

**Example Injection Block:**
```bash
# Workforce Nexus Block START
export PATH="$HOME/.mcp-tools/bin:$PATH"
# Workforce Nexus Block END
```
*The uninstall script specifically targets everything between these markers.*

### User Wrappers (Default Short Commands)
By default, Industrial installs also place **short-command wrapper scripts** in a common user-owned directory:
* `~/.local/bin`

These wrappers do **not** require editing `~/.zshrc` and allow running commands from any directory:
* `mcp-activator`, `mcp-surgeon`, `mcp-observer`, `mcp-librarian`

If `~/.local/bin` is not on your PATH, add it manually (recommended):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Installer Re-runs (First run vs re-run)
`bootstrap.py` persists a small state file under:
* `~/.mcp-tools/.nexus_state.json`

On a re-run, it shows a menu to **repair/sync**, **configure injection**, **launch the GUI**, or **uninstall**, instead of silently skipping steps.

### IDE Injection Policy (Startup Detect)
* The injector supports startup client discovery (prompt-before-mutate).
* `claude` is included in the common prompt set.
* If Nexus-created binaries exist (`~/.mcp-tools/bin`), the injector prompts per component instead of blind bulk injection.

### One-Repo Suite Installation (Central Clone)
If you have only a single repo checked out, forwarder bootstraps support:
* `python3 bootstrap.py --install-suite --permanent`

This clones missing Nexus repos into `~/.mcp-tools` (no disk scanning) and then runs the Activator bootstrap.

### Uninstall Policy (Central-only, confirmable)
Canonical uninstall lives in this repo and supports:
* `--dry-run` to preview deletions
* `--verbose` for more detail
* `--devlog` to capture actions to the shared devlog
* `--kill-venv` to remove the shared venv (kept by default)
* `--purge-data` to remove shared suite data under `~/.mcp-tools` / `~/.mcpinv`

When purging, uninstall also removes Nexus-managed wrapper scripts from:
* `~/.local/bin` (only wrapper files containing the Nexus marker)

### Optional Extra Repos
If you want the activator to install/update additional git repos alongside the Nexus suite, you can add an `extra_repos` map to `~/.mcp-tools/config.json`:
```json
{
  "extra_repos": {
    "my-private-tooling": "git@github.com:your-org/my-private-tooling.git"
  }
}
```
Notes:
* Prefer SSH URLs; avoid embedding access tokens in config files.
* These repos are fetched/updated during `bootstrap.py --repair` (GitHub mode) and installed into `~/.mcp-tools/<repo-name>`.

### Permissions Hardening (Phase 9)
The environment must support `chmod` (POSIX) or equivalent ACL modifications.
* **Logic**: During installation, entry points and scripts are marked executable as needed.

---

## 🛡 Network & Proxy Requirements
* **Discovery**: Requires outbound access to `github.com` for bootstrapping missing repos.
* **Installation**: Requires access to `pypi.org` (and optional `registry.npmjs.org` if Node tooling is needed).
* **Air-gap Mode**: If dependencies are pre-cached, `--lite` can run without active network connections.

---

## 📝 Metadata
* **Status**: Hardened
* **Reference**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)
