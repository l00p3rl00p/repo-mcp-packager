# Codebase Audit Findings: Workforce Nexus

**Date**: 2026-02-11
**Scope**: `mcp-injector`, `mcp-server-manager`, `mcp-link-library`, `repo-mcp-packager`
**Status**: Stable (Industrial Tier)

## A) Findings Table (Prioritized)

| Severity | Category | Location | Symptom | Risk | Recommended Fix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **High** | Security | `mcp_inventory/gui.py` (L190-205) | JSON Payload parsing inside `do_POST` lacks strict schema validation before processing. | Malformed JSON could crash the server thread or inject unexpected types. | Use `jsonschema` (tier-aware) or explicit type checks before accessing `post_data`. |
| **Medium** | Error Handling | `mcp_inventory/gui.py` (L231) | `subprocess.Popen` used for async task without tracking child PID lifecycle. | Zombie processes if the GUI crashes or is killed forcefully. | Store `process.pid` in a `runtime.json` state file to cleanup on startup. |
| **Medium** | Security | `mcp_link_library/mcp.py` (L637) | `_read_resource` validates `cwd` purely by string path. | Symlink attacks could bypass CWD check if the symlink resolves outside. | Use `path.resolve().is_relative_to(cwd)` (Py3.9+) or strict common prefix check. |
| **Low** | Documentation | `mcp_injector/mcp_injector.py` (L28) | `inject_nexus_env` modifies `sys.path`. | Side-effects on import system are opaque to callers. | Add docstring warning: "SIDE EFFECT: Modifies sys.path explicitly." |
| **Low** | Error Handling | `repo-mcp-packager/bootstrap.py` (L439) | Bare `except Exception as e` in main catch-all. | Swallows `KeyboardInterrupt` (Ctrl+C) prevents clean exit. | Catch `Exception` separate from `KeyboardInterrupt` to handle user aborts gracefully. |

## B) Major Update Determination

**Is this a MAJOR UPDATE?** -> **NO**

**Reasoning**:
1.  **Security**: No critical vulnerabilities (e.g., remote code execution, secret leakage) found. Path traversal protections (`resolve()`, `cwd` checks) are present.
2.  **Error Handling**: Global `try/except` blocks exist in all entry points (`main()`), preventing hard crashes.
3.  **Stability**: The "Industrial" tier hardening (venvs, permissions) mitigates most supply chain risks.

## C) Recommended Minor Hardening (Next Steps)
While not a major update, the following *Standard* polish is recommended:
1.  **Fix Zombie Processes**: Add a `atexit` handler in `gui.py` to kill spawned subprocesses.
2.  **Explicit Interrupt Handling**: Update `bootstrap.py` to handle `Ctrl+C` cleanly without printing stack traces.
3.  **Logging**: Standardize on `logging` module instead of `print` for non-CLI tools (`mcp.py`).
