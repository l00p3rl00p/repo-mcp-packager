import os
import shutil
import json
import argparse
import sys
import datetime
import time
from pathlib import Path
from typing import List
from typing import Optional

# Import attach module for MCP removal
try:
    sys.path.append(str(Path(__file__).parent))
    from attach import remove_from_clients
    MCP_REMOVAL_AVAILABLE = True
except ImportError:
    MCP_REMOVAL_AVAILABLE = False

def get_mcp_tools_home():
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

def _home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())).expanduser()

def _devlog_dir() -> Path:
    # Keep devlogs outside ~/.mcp-tools so a purge can still leave a forensic trail (when requested).
    return _home() / ".mcpinv" / "devlogs"

def _prune_old_devlogs(devlog_dir: Path, days: int = 90, verbose: bool = False) -> None:
    try:
        devlog_dir.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        for p in devlog_dir.glob("nexus-*.jsonl"):
            try:
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
                if mtime < cutoff:
                    if verbose:
                        print(f"[-] Pruning old devlog: {p}")
                    p.unlink(missing_ok=True)
            except Exception:
                continue
    except Exception:
        return

def _devlog_path() -> Path:
    # One file per day to simplify retention pruning.
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    return _devlog_dir() / f"nexus-{stamp}.jsonl"

def _write_devlog(path: Path, event: str, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "event": event,
            **data,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # devlog should never block uninstall
        return

def _confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    r = input(f"{prompt} [y/N]: ").strip().lower()
    return r == "y" or r == "yes"

def _remove_path_block(verbose: bool = False, devlog: Optional[Path] = None) -> None:
    """
    Remove PATH injection block created by bootstrap.py ensure_global_path().
    This is intentionally limited to known marker strings; no directory traversal.
    """
    marker_start = "# Workforce Nexus Block START"
    marker_end = "# Workforce Nexus Block END"

    shell = os.environ.get("SHELL", "")
    candidates: List[Path] = []
    if "zsh" in shell:
        candidates.append(_home() / ".zshrc")
    if "bash" in shell:
        candidates.append(_home() / ".bashrc")
    # Also try both common files if shell env is missing.
    candidates.extend([_home() / ".zshrc", _home() / ".bashrc"])

    seen = set()
    for rc in candidates:
        if rc in seen:
            continue
        seen.add(rc)
        if not rc.exists() or not rc.is_file():
            continue
        try:
            content = rc.read_text(encoding="utf-8", errors="ignore").splitlines()
            if marker_start not in "\n".join(content):
                continue

            backup = rc.with_suffix(rc.suffix + f".backup.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            try:
                backup.write_text("\n".join(content) + "\n", encoding="utf-8")
            except Exception:
                pass

            new_lines = []
            inside = False
            for line in content:
                if line.strip() == marker_start:
                    inside = True
                    continue
                if line.strip() == marker_end:
                    inside = False
                    continue
                if not inside:
                    new_lines.append(line)
            rc.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            if verbose:
                print(f"[-] Removed PATH block from {rc} (backup: {backup})")
            if devlog:
                _write_devlog(devlog, "path_block_removed", {"file": str(rc), "backup": str(backup)})
        except Exception:
            continue

def _remove_user_wrappers(verbose: bool = False, devlog: Optional[Path] = None) -> None:
    """
    Remove short-command wrapper scripts created by repo-mcp-packager bootstrap.
    This is scoped to a single, common user-owned bin directory; no disk scans.
    """
    if sys.platform == "win32":
        return

    wrappers_dir = _home() / ".local" / "bin"
    marker = "# Workforce Nexus User Wrapper (managed by repo-mcp-packager)"
    names = ("mcp-surgeon", "mcp-observer", "mcp-librarian", "mcp-activator")

    for name in names:
        p = wrappers_dir / name
        try:
            if not p.exists() or not p.is_file():
                continue
            content = p.read_text(encoding="utf-8", errors="ignore")
            if marker not in content:
                continue
            p.unlink(missing_ok=True)
            if verbose:
                print(f"[-] Removed user wrapper: {p}")
            if devlog:
                _write_devlog(devlog, "user_wrapper_removed", {"path": str(p)})
        except Exception:
            continue

def _remove_desktop_launchers(verbose: bool = False, devlog: Optional[Path] = None) -> None:
    """
    Remove Desktop launchers created by setup.sh (macOS .command / Windows .bat).
    This is intentionally scoped to known filenames; no directory scans.
    """
    try:
        home = _home()
        desktop = home / "Desktop"
        if not desktop.exists():
            return
        targets = [
            desktop / "Start Nexus.command",
            desktop / "Start Nexus.bat",
        ]
        for p in targets:
            try:
                if not p.exists():
                    continue
                p.unlink(missing_ok=True)
                if verbose:
                    print(f"[-] Removed Desktop launcher: {p}")
                if devlog:
                    _write_devlog(devlog, "desktop_launcher_removed", {"path": str(p)})
            except Exception:
                continue
    except Exception:
        return

def _remove_shell_aliases(verbose: bool = False, devlog: Optional[Path] = None) -> None:
    """
    Best-effort removal of legacy alias lines added by setup.sh (no markers).
    Conservatively removes only aliases that point at missing files.
    """
    try:
        home = _home()
        candidates: list[Path] = []
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            candidates.append(home / ".zshrc")
        if "bash" in shell:
            candidates.append(home / ".bash_profile")
            candidates.append(home / ".bashrc")
        candidates.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

        seen: set[Path] = set()
        for rc in candidates:
            if rc in seen:
                continue
            seen.add(rc)
            if not rc.exists() or not rc.is_file():
                continue
            try:
                raw_lines = rc.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue

            removed = 0
            kept: list[str] = []
            for line in raw_lines:
                s = line.strip()
                if not s.startswith("alias "):
                    kept.append(line)
                    continue
                if ("nexus-verify.py" not in s) and ("/nexus.sh" not in s):
                    kept.append(line)
                    continue
                # Heuristic: extract the first quoted path and remove the alias only if that path no longer exists.
                # Example lines:
                #   alias nx='python3 /abs/path/nexus-verify.py'
                #   alias nexus='/abs/path/nexus.sh'
                target_path = None
                for token in ("nexus-verify.py", "/nexus.sh"):
                    idx = s.find(token)
                    if idx == -1:
                        continue
                    # Walk backwards to find a plausible path boundary
                    start = s.rfind(" ", 0, idx)
                    if start == -1:
                        start = s.rfind("'", 0, idx)
                    if start == -1:
                        start = 0
                    candidate = s[start: idx + len(token)].strip(" '\"")
                    if candidate:
                        target_path = candidate
                        break
                if target_path:
                    try:
                        if not Path(target_path).expanduser().exists():
                            removed += 1
                            continue
                    except Exception:
                        pass
                kept.append(line)

            if removed <= 0:
                continue

            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup = rc.with_suffix(rc.suffix + f".backup.{stamp}")
            try:
                backup.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
            except Exception:
                pass
            try:
                rc.write_text("\n".join(kept) + "\n", encoding="utf-8")
                if verbose:
                    print(f"[-] Removed {removed} alias line(s) from {rc} (backup: {backup})")
                if devlog:
                    _write_devlog(devlog, "shell_aliases_removed", {"file": str(rc), "removed": removed, "backup": str(backup)})
            except Exception:
                continue
    except Exception:
        return

def _terminate_nexus_processes(verbose: bool = False, devlog: Optional[Path] = None) -> None:
    """
    Best-effort: terminate running Nexus-related processes so a wipe is actually pristine.
    This is intentionally conservative and avoids broad "kill python" behavior.
    """
    try:
        # First, try PID files written by launchers/tray. This avoids any need for
        # process enumeration (ps/psutil) and is the most reliable cross-env signal.
        try:
            pid_paths = [
                _home() / ".mcpinv" / "nexus.pid",
            ]
            for pid_path in pid_paths:
                try:
                    if not pid_path.exists():
                        continue
                    raw = pid_path.read_text(encoding="utf-8", errors="ignore").strip()
                    pid = int(raw) if raw.isdigit() else None
                    if not pid or pid == os.getpid():
                        continue
                    try:
                        os.kill(pid, 15)  # SIGTERM
                        time.sleep(0.3)
                        os.kill(pid, 9)  # SIGKILL (if still alive)
                    except Exception:
                        pass
                    try:
                        pid_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    if verbose:
                        print(f"[-] Terminated Nexus PID from pidfile: {pid} ({pid_path})")
                    if devlog:
                        _write_devlog(devlog, "process_terminated_pidfile", {"pid": pid, "pidfile": str(pid_path)})
                except Exception:
                    continue
        except Exception:
            pass

        patterns = (
            "nexus_tray.py",
            "gui_bridge.py",
            "mcp_inventory",
            "mcp_injector.py",
            "repo-mcp-packager",
            ".mcp-tools",
        )
        me = os.getpid()
        killed: list[dict] = []

        try:
            import psutil  # type: ignore
        except Exception:
            psutil = None  # type: ignore

        if psutil is None:
            return

        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if not pid or pid == me:
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(str(x) for x in cmdline)
                if not cmd:
                    continue
                cmd_l = cmd.lower()
                if not any(p.lower() in cmd_l for p in patterns):
                    continue
                # Avoid killing unrelated processes that just happen to mention "mcp"
                if ("nexus_tray.py" not in cmd_l) and (".mcp-tools" not in cmd_l) and ("repo-mcp-packager" not in cmd_l):
                    continue
                proc.terminate()
                killed.append({"pid": pid, "cmd": cmd[:240]})
            except Exception:
                continue

        # Give graceful terminate a moment, then hard kill any survivors we targeted.
        try:
            psutil.wait_procs([psutil.Process(k["pid"]) for k in killed], timeout=2)  # type: ignore[arg-type]
        except Exception:
            pass
        for k in killed:
            try:
                p = psutil.Process(k["pid"])
                if p.is_running():
                    p.kill()
            except Exception:
                continue

        if killed and verbose:
            print(f"[-] Terminated Nexus-related processes: {len(killed)}")
        if devlog and killed:
            _write_devlog(devlog, "processes_terminated", {"count": len(killed), "procs": killed})
    except Exception:
        return

def _purge_checklist_path() -> Optional[Path]:
    """
    Location for a human-facing purge checklist that survives a full wipe.
    Prefer Desktop so it doesn't interfere with a new install and is easy to find.
    """
    try:
        home = _home()
        desktop = home / "Desktop"
        base = desktop if desktop.exists() else home
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return base / f"Nexus Purge Checklist {stamp}.md"
    except Exception:
        return None

def _write_purge_checklist(path: Path, sections: list[tuple[str, list[str]]]) -> None:
    try:
        lines: list[str] = []
        lines.append("# Nexus Purge Checklist")
        lines.append("")
        lines.append(f"- Timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"- Platform: {sys.platform}")
        lines.append("")
        for title, items in sections:
            lines.append(f"## {title}")
            lines.append("")
            if not items:
                lines.append("- (none)")
                lines.append("")
                continue
            for it in items:
                lines.append(f"- {it}")
            lines.append("")
        lines.append("## Next steps")
        lines.append("")
        lines.append("- Reinstall: run `./nexus.sh` from a fresh workspace clone, or re-run your installer.")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        return

def _client_config_paths() -> list[tuple[str, Path]]:
    """
    Best-effort detection of MCP client config files for uninstall cleanup.

    This avoids importing the injector (which may already be partially removed during purge).
    """
    home = _home()
    out: list[tuple[str, Path]] = []
    if sys.platform == "darwin":
        out.append(("claude", home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"))
        out.append(("codex", home / "Library" / "Application Support" / "Codex" / "mcp_servers.json"))
        out.append(("xcode", home / "Library" / "Developer" / "Xcode" / "UserData" / "MCPServers" / "config.json"))
    elif sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(home)))
        localapp = Path(os.environ.get("LOCALAPPDATA", str(home)))
        out.append(("claude", appdata / "Claude" / "claude_desktop_config.json"))
        out.append(("codex", appdata / "Codex" / "mcp_servers.json"))
        out.append(("xcode", localapp / "Xcode" / "MCPServers" / "config.json"))
    else:
        # Linux: best-effort locations (may vary by packaging).
        out.append(("claude", home / ".config" / "Claude" / "claude_desktop_config.json"))
        out.append(("codex", home / ".config" / "Codex" / "mcp_servers.json"))
    return out

def _looks_like_suite_server(name: str, server_def: object) -> bool:
    try:
        n = (name or "").lower()
        if n.startswith("nexus-") or n.startswith("mcp-"):
            # avoid nuking user servers named mcp-foo; rely on command path check too
            pass

        cmd = ""
        if isinstance(server_def, dict):
            cmd = str(server_def.get("command") or "")
        cmd_l = cmd.lower()
        return (".mcp-tools" in cmd_l) or ("mcp-tools" in cmd_l) or n.startswith("nexus-")
    except Exception:
        return False

def _looks_like_managed_server(name: str, server_def: object) -> bool:
    """Servers typically created/managed under ~/.mcp-tools/servers/*."""
    try:
        cmd = ""
        if isinstance(server_def, dict):
            cmd = str(server_def.get("command") or "")
        cmd_l = cmd.lower()
        return ("/.mcp-tools/servers/" in cmd_l) or ("\\.mcp-tools\\servers\\" in cmd_l) or ("/mcp-tools/servers/" in cmd_l)
    except Exception:
        return False

def _looks_like_suite_tool(name: str, server_def: object) -> bool:
    """Core suite tools (nexus-*) and commands pointing to ~/.mcp-tools/bin."""
    try:
        n = (name or "").lower()
        if n.startswith("nexus-"):
            return True
        cmd = ""
        if isinstance(server_def, dict):
            cmd = str(server_def.get("command") or "")
        cmd_l = cmd.lower()
        return "/.mcp-tools/bin/" in cmd_l or "\\.mcp-tools\\bin\\" in cmd_l
    except Exception:
        return False

def _detach_suite_from_client_config(
    path: Path,
    *,
    verbose: bool = False,
    devlog: Optional[Path] = None,
    detach_suite: bool = True,
    detach_managed: bool = False,
    detach_suite_tools: bool = False,
) -> int:
    """
    Remove suite-installed servers from a client config JSON file.

    Heuristics:
    - detach_suite: historical behavior (broad) — remove servers whose command points into ~/.mcp-tools OR name starts with nexus-
    - detach_managed: remove servers that point into ~/.mcp-tools/servers/*
    - detach_suite_tools: remove core suite tools (nexus-* / ~/.mcp-tools/bin/*)
    """
    try:
        if not path.exists() or not path.is_file():
            return 0
        raw = path.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return 0

        removed = 0

        # Common shapes: {mcpServers: {...}} or {mcp_servers: {...}}.
        def _should_remove(k: str, v: object) -> bool:
            if detach_suite:
                return _looks_like_suite_server(k, v)
            remove = False
            if detach_managed:
                remove = remove or _looks_like_managed_server(k, v)
            if detach_suite_tools:
                remove = remove or _looks_like_suite_tool(k, v)
            return remove

        for key in ("mcpServers", "mcp_servers", "servers"):
            block = data.get(key)
            if isinstance(block, dict):
                doomed = [k for k, v in block.items() if _should_remove(k, v)]
                for k in doomed:
                    try:
                        del block[k]
                        removed += 1
                    except Exception:
                        continue

        if removed <= 0:
            return 0

        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        backup = path.with_suffix(path.suffix + f".backup.{stamp}")
        try:
            backup.write_text(raw, encoding="utf-8")
        except Exception:
            pass

        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if verbose:
            print(f"[-] Detached {removed} suite server(s) from {path}")
        if devlog:
            _write_devlog(devlog, "client_detach", {"path": str(path), "removed": removed, "backup": str(backup)})
        return removed
    except Exception as e:
        if verbose:
            print(f"[warn] Client detach failed for {path}: {e}")
        if devlog:
            _write_devlog(devlog, "client_detach_failed", {"path": str(path), "error": str(e)})
        return 0


class NexusUninstaller:
    def __init__(
        self,
        project_root: Path,
        kill_venv: bool = False,
        purge_data: bool = False,
        purge_env: bool = False,
        verbose: bool = False,
        devlog: Optional[Path] = None,
        yes: bool = False,
        dry_run: bool = False,
    ):
        self.project_root = project_root
        self.kill_venv = kill_venv
        self.purge_data = purge_data
        self.purge_env = purge_env
        self.verbose = verbose
        self.devlog = devlog
        self.yes = yes
        self.dry_run = dry_run
        self.manifest_path = self.project_root / ".librarian" / "manifest.json"

    def log(self, msg: str):
        print(f"[-] {msg}")
        if self.devlog:
            _write_devlog(self.devlog, "log", {"message": msg})

    def run(self):
        # If purge_data is requested, we operate in "central-only" mode. We do NOT scan the disk
        # and we do NOT attempt to clean workspace artifacts automatically.
        if self.purge_data:
            return self.run_central_only()
        if self.purge_env:
            return self.run_central_env_only()

        if not self.manifest_path.exists():
            print(f"[warn] No installation manifest found at {self.manifest_path}.")
            print("   Proceeding with directory clean-up mode (fallback).")
            manifest = {}
        else:
            try:
                with open(self.manifest_path, 'r') as f:
                    manifest = json.load(f)
            except Exception:
                stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                backup = self.manifest_path.with_suffix(f".json.corrupt.{stamp}")
                try:
                    self.manifest_path.replace(backup)
                    if self.devlog:
                        _write_devlog(self.devlog, "manifest_corrupt_recovered", {"backup": str(backup)})
                    if self.verbose:
                        print(f"[-] Recovered malformed manifest. Backup: {backup}")
                except Exception:
                    pass
                manifest = {}

        # Remove MCP attachments first (if any)
        if "attached_clients" in manifest:
            self.remove_mcp_attachments(manifest["attached_clients"])

        artifacts = manifest.get("install_artifacts", [])
        if artifacts:
            self.log(f"Found {len(artifacts)} tracked artifacts for removal.")

        # 1. Remove tracked artifacts (files/dirs or surgical blocks)
        # Backward compatible: remove legacy markers used across prior iterations.
        marker_pairs = [
            ("# Workforce Nexus Block START", "# Workforce Nexus Block END"),
            ("# Nexus Block START", "# Nexus Block END"),
            ("# Shesha Block START", "# Shesha Block END"),
        ]

        for path_str in artifacts:
            path = Path(path_str)
            if not path.exists():
                continue

            # Check for surgical markers in ANY file
            is_surgical = False
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    if any(ms in content for ms, _ in marker_pairs):
                        is_surgical = True
                except Exception:
                    pass

            if is_surgical:
                self.log(f"Surgically reversing environment changes in: {path}")
                lines = path.read_text(encoding="utf-8").splitlines()
                new_lines = []
                inside_block = False
                active_end = None
                for line in lines:
                    stripped = line.strip()
                    if not inside_block:
                        for ms, me in marker_pairs:
                            if stripped == ms:
                                inside_block = True
                                active_end = me
                                break
                        if inside_block:
                            continue
                        new_lines.append(line)
                        continue

                    # inside a surgical block
                    if active_end and stripped == active_end:
                        inside_block = False
                        active_end = None
                        continue
                
                path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                continue

            # Standard removal for directories/files
            if path.is_dir():
                self.log(f"Removing directory: {path}")
                shutil.rmtree(path, ignore_errors=True)
            else:
                self.log(f"Removing file: {path}")
                path.unlink(missing_ok=True)

        # 2. Cleanup manifest directory (if it exists)
        manifest_dir = self.manifest_path.parent
        if manifest_dir.exists():
            self.log(f"Removing manifest directory: {manifest_dir}")
            shutil.rmtree(manifest_dir, ignore_errors=True)

        # 3. Handle Venv
        if self.kill_venv:
            venv_path = self.project_root / ".venv"
            if venv_path.exists():
                self.log(f"Killing virtual environment: {venv_path}")
                shutil.rmtree(venv_path, ignore_errors=True)
        else:
            self.log("Skipping virtual environment removal (use --kill-venv to remove).")

        self.log("Uninstall complete. System restored.")

        # 4. Handle Shared Nexus (Lifecycle Management)
        if self.purge_data:
            self.remove_nexus(force=True)
        else:
            self.remove_nexus(force=False)

    def run_central_only(self):
        nexus = get_mcp_tools_home()
        mcpinv = _home() / ".mcpinv"

        targets: List[tuple[str, Path, str]] = []
        checklist = _purge_checklist_path() if self.kill_venv else None
        actions: list[str] = []

        # If we are doing a true wipe, stop the running tray/bridge first; a deleted folder
        # doesn't stop a backgrounded Python process.
        if self.kill_venv:
            _terminate_nexus_processes(verbose=self.verbose, devlog=self.devlog)
            actions.append("Attempted to terminate running Nexus processes (best-effort).")

        # Central suite cleanup:
        # - If --kill-venv is set: delete ~/.mcp-tools entirely (includes .venv)
        # - If --kill-venv is NOT set: delete everything under ~/.mcp-tools EXCEPT .venv
        # Optional: detach from IDE clients BEFORE deleting ~/.mcp-tools (since it contains injector code).
        if getattr(self, "detach_clients", False):
            removed_total = 0
            for _, cfg in _client_config_paths():
                removed_total += _detach_suite_from_client_config(
                    cfg,
                    verbose=self.verbose,
                    devlog=self.devlog,
                    detach_suite=True,
                )
            if self.verbose:
                print(f"[-] Detached suite servers from clients: removed={removed_total}")
            actions.append(f"Detached suite servers from IDE client configs: removed={removed_total}")

        if getattr(self, "remove_path_block", False):
            _remove_path_block(verbose=self.verbose, devlog=self.devlog)
            actions.append("Removed PATH injection block markers (best-effort).")
        if getattr(self, "remove_wrappers", False):
            _remove_user_wrappers(verbose=self.verbose, devlog=self.devlog)
            actions.append("Removed user wrapper scripts in ~/.local/bin (best-effort).")

        # Remove Desktop launchers so a "wipe" doesn't leave a working entrypoint behind.
        if self.kill_venv:
            _remove_desktop_launchers(verbose=self.verbose, devlog=self.devlog)
            actions.append("Removed Desktop launchers: Start Nexus.command / Start Nexus.bat (best-effort).")
            # Legacy aliases are unmarked; remove only the ones pointing at missing files.
            _remove_shell_aliases(verbose=self.verbose, devlog=self.devlog)
            actions.append("Removed legacy shell aliases pointing at missing Nexus files (best-effort).")

        if nexus.exists():
            venv = nexus / ".venv"
            if self.kill_venv:
                targets.append(("dir", nexus, "central suite (~/.mcp-tools) + venv"))
            else:
                # Keep the venv (anti-lazy: preserve heavy install if user wants)
                for child in sorted(nexus.iterdir(), key=lambda p: p.name):
                    if child.name == ".venv":
                        continue
                    targets.append(("dir" if child.is_dir() else "file", child, "central suite component"))

        # Observer state/logs cleanup
        # If --devlog is enabled, preserve ~/.mcpinv/devlogs so the forensic trail survives the purge.
        if mcpinv.exists():
            if self.devlog:
                for child in sorted(mcpinv.iterdir(), key=lambda p: p.name):
                    if child.name == "devlogs":
                        targets.append(("dir", child, "kept: devlogs (~/.mcpinv/devlogs)"))
                        continue
                    targets.append(("dir" if child.is_dir() else "file", child, "observer state/logs component"))
            else:
                targets.append(("dir", mcpinv, "observer state/logs (~/.mcpinv)"))

        # Deduplicate (if deleting ~/.mcp-tools, venv is implicitly included)
        deduped: List[tuple[str, Path, str]] = []
        seen = set()
        for kind, path, reason in targets:
            if path in seen:
                continue
            seen.add(path)
            deduped.append((kind, path, reason))

        print("\nNexus Uninstall (Central-Only)")
        print("=" * 60)
        if deduped:
            print("Planned removals:")
            for kind, path, reason in deduped:
                print(f"- {kind:3} {path}  ({reason})")
        else:
            print("Nothing found to remove in approved locations.")

        print("\nSafety note:")
        print("- This uninstaller will NOT scan your disk or walk up directories.")
        print("- It will NOT delete anything in your git workspace automatically.")
        if self.devlog:
            print(f"- Devlog enabled: keeping {(_home() / '.mcpinv' / 'devlogs')}")
        print("\nWorkspace cleanup (manual):")
        print("- If you created local venvs in your repo folders, delete them yourself, e.g.:")
        print("  - From each repo root: rm -rf .venv __pycache__ .pytest_cache")
        if checklist:
            print("\nPurge checklist:")
            print(f"- Will be written to: {checklist}")

        # Confirmation rules:
        # - --purge-data always requires confirmation
        # - --kill-venv is explained as the “destroy environments” flag
        if deduped:
            print()
            if not self.kill_venv:
                print("[info] --kill-venv not set: preserving ~/.mcp-tools/.venv (if present).")
                print("   If you want a complete wipe (including environments), re-run with --kill-venv.")
            if not self.yes and not _confirm("Proceed with deleting the above items?"):
                self.log("User aborted uninstall.")
                if self.devlog:
                    _write_devlog(self.devlog, "aborted", {"targets": [str(p) for _, p, _ in deduped]})
                return 2

        if self.dry_run:
            self.log("Dry-run enabled; no changes were made.")
            if self.devlog:
                _write_devlog(self.devlog, "dry_run", {"targets": [str(p) for _, p, _ in deduped]})
            return 0

        # Optional PATH cleanup (only when explicitly requested).
        if getattr(self, "remove_path_block", False):
            _remove_path_block(verbose=self.verbose, devlog=self.devlog)
        if getattr(self, "remove_wrappers", False):
            _remove_user_wrappers(verbose=self.verbose, devlog=self.devlog)

        # Perform deletions (skip any “kept” markers)
        for kind, path, reason in deduped:
            if reason.startswith("kept:"):
                if self.verbose:
                    print(f"[-] Keeping: {path}")
                if self.devlog:
                    _write_devlog(self.devlog, "kept", {"path": str(path), "reason": reason})
                continue
            try:
                if path.is_dir():
                    if self.verbose:
                        print(f"[-] Removing directory: {path}")
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    if self.verbose:
                        print(f"[-] Removing file: {path}")
                    path.unlink(missing_ok=True)
                if self.devlog:
                    _write_devlog(self.devlog, "removed", {"path": str(path), "reason": reason})
            except Exception as e:
                print(f"[warn] Failed to remove {path}: {e}")
                if self.devlog:
                    _write_devlog(self.devlog, "remove_failed", {"path": str(path), "error": str(e), "reason": reason})

        if checklist:
            _write_purge_checklist(
                checklist,
                [
                    ("Actions performed", actions + [f"Checklist written to: {checklist}"]),
                    ("Planned removals (targets)", [f"{k} {p} ({r})" for (k, p, r) in deduped]),
                    ("Notes", ["Uninstaller operates only in approved locations (no disk scan)."]),
                ],
            )
            if self.verbose:
                print(f"[-] Wrote purge checklist: {checklist}")

        self.log("Uninstall complete (central-only).")
        return 0

    def run_central_env_only(self):
        """
        Purge only environments (rebuildable), keeping suite binaries and data in ~/.mcp-tools.
        Safe default for most “it’s broken” cases.
        """
        nexus = get_mcp_tools_home()
        targets: List[tuple[str, Path, str]] = []

        if getattr(self, "detach_managed_servers", False) or getattr(self, "detach_suite_tools", False):
            removed_total = 0
            for _, cfg in _client_config_paths():
                removed_total += _detach_suite_from_client_config(
                    cfg,
                    verbose=self.verbose,
                    devlog=self.devlog,
                    detach_suite=False,
                    detach_managed=bool(getattr(self, "detach_managed_servers", False)),
                    detach_suite_tools=bool(getattr(self, "detach_suite_tools", False)),
                )
            if self.verbose:
                print(f"[-] Detached servers from clients: removed={removed_total}")

        if nexus.exists():
            venv = nexus / ".venv"
            if venv.exists():
                targets.append(("dir", venv, "central env (~/.mcp-tools/.venv)"))

            servers_dir = nexus / "servers"
            if servers_dir.exists() and servers_dir.is_dir():
                for srv in sorted(servers_dir.iterdir(), key=lambda p: p.name):
                    v = srv / ".venv"
                    if v.exists():
                        targets.append(("dir", v, "server env (servers/*/.venv)"))

        print("\nNexus Uninstall (Env-Only)")
        print("=" * 60)
        if targets:
            print("Planned removals:")
            for kind, path, reason in targets:
                print(f"- {kind:3} {path}  ({reason})")
        else:
            print("Nothing found to remove in approved locations.")

        if targets:
            print()
            print("[info] This keeps suite binaries and data; only environments are removed.")
            if not self.yes and not _confirm("Proceed with deleting the above items?"):
                self.log("User aborted uninstall.")
                if self.devlog:
                    _write_devlog(self.devlog, "aborted", {"targets": [str(p) for _, p, _ in targets]})
                return 2

        if self.dry_run:
            self.log("Dry-run enabled; no changes were made.")
            if self.devlog:
                _write_devlog(self.devlog, "dry_run", {"targets": [str(p) for _, p, _ in targets]})
            return 0

        for kind, path, reason in targets:
            try:
                if path.is_dir():
                    if self.verbose:
                        print(f"[-] Removing directory: {path}")
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    if self.verbose:
                        print(f"[-] Removing file: {path}")
                    path.unlink(missing_ok=True)
                if self.devlog:
                    _write_devlog(self.devlog, "removed", {"path": str(path), "reason": reason})
            except Exception as e:
                print(f"[warn] Failed to remove {path}: {e}")
                if self.devlog:
                    _write_devlog(self.devlog, "remove_failed", {"path": str(path), "error": str(e), "reason": reason})

        self.log("Uninstall complete (env-only).")
        return 0

    def remove_nexus(self, force: bool = False):
        """Check if we should remove the shared Nexus root (~/.mcp-tools)."""
        nexus = get_mcp_tools_home()
        if not nexus.exists():
            return
            
        if force:
            self.log(f"🔥 PURGING shared Nexus data at {nexus}...")
            shutil.rmtree(nexus, ignore_errors=True)
            return

        # Check for siblings
        # We expect folders like: mcp-server-manager, mcp-link-library, mcp-injector, repo-mcp-packager
        siblings = [p for p in nexus.iterdir() if p.is_dir()]
        
        # If we are running from INSIDE the nexus, we count as one.
        # But we already deleted our own folder in step 1 (if manifest was correct).
        # Let's see what's left.
        remaining = len(siblings)
        
        if remaining > 1:
            self.log(f"[info] Keeping shared Nexus ({remaining} tools detected).")
        elif remaining == 1:
            # Often the last folder is just an empty shell or a config file
            # Let's ask the user
            print("\n[warn] You seem to be the last tool standing.")
            print(f"   Nexus location: {nexus}")
            print(f"   Contents: {[s.name for s in siblings]}")
            choice = input(f"   Remove shared Nexus data and config? [y/N]: ").strip().lower()
            if choice == 'y':
                self.log(f"Removing shared Nexus: {nexus}")
                shutil.rmtree(nexus, ignore_errors=True)
            else:
                self.log("Keeping shared Nexus.")
        else:
            # Empty nexus?
            self.log("Removing empty Nexus directory.")
            shutil.rmtree(nexus, ignore_errors=True)
    
    def remove_mcp_attachments(self, attached_clients: list):
        """Remove MCP server entries from IDE configs"""
        if not MCP_REMOVAL_AVAILABLE:
            self.log("[warn] MCP removal not available. Skipping IDE config cleanup.")
            return
        
        self.log(f"Removing MCP attachments from {len(attached_clients)} IDE(s)...")
        
        # Extract server name from first entry (all should be the same)
        if not attached_clients:
            return
        
        server_name = attached_clients[0].get("server_key")
        if not server_name:
            return
        
        results = remove_from_clients(server_name, attached_clients)
        
        success_count = sum(1 for r in results if r.success)
        self.log(f"Removed from {success_count}/{len(results)} IDE config(s)")

def main():
    parser = argparse.ArgumentParser(description="Nexus Clean Room Uninstaller")
    parser.add_argument("--kill-venv", action="store_true", help="Remove the virtual environment as well")
    parser.add_argument("--purge-data", action="store_true", help="Remove central suite data (~/.mcp-tools) and observer state (~/.mcpinv)")
    parser.add_argument("--purge-env", action="store_true", help="Remove only shared environments (keep suite installed)")
    parser.add_argument("--detach-clients", action="store_true", help="Remove suite servers from detected IDE client configs")
    parser.add_argument("--detach-managed-servers", action="store_true", help="Detach managed servers (e.g., ~/.mcp-tools/servers/*) from clients")
    parser.add_argument("--detach-suite-tools", action="store_true", help="Detach suite tools (nexus-*) from clients")
    parser.add_argument("--remove-path-block", action="store_true", help="Remove PATH injection block from shell rc files")
    parser.add_argument("--remove-wrappers", action="store_true", help="Remove user wrapper scripts (e.g., ~/.local/bin/mcp-*)")
    # NOTE: Desktop launchers + legacy aliases are removed automatically on --kill-venv full wipe.
    parser.add_argument("--verbose", action="store_true", help="Verbose output (print every decision + removal)")
    parser.add_argument("--devlog", action="store_true", help="Write a dev log (JSONL) with 90-day retention")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts (DANGEROUS)")
    parser.add_argument("--dry-run", action="store_true", help="Print planned removals, but do not delete anything")
    args = parser.parse_args()

    root = Path(__file__).parent.parent.resolve()
    devlog_path = None
    if args.devlog:
        _prune_old_devlogs(_devlog_dir(), days=90, verbose=args.verbose)
        devlog_path = _devlog_path()
        _write_devlog(devlog_path, "start", {"cmd": "uninstall", "kill_venv": args.kill_venv, "purge_data": args.purge_data})
        if args.verbose:
            print(f"[-] Devlog: {devlog_path}")

    uninstaller = NexusUninstaller(
        root,
        kill_venv=args.kill_venv,
        purge_data=args.purge_data,
        purge_env=args.purge_env,
        verbose=args.verbose,
        devlog=devlog_path,
        yes=args.yes,
        dry_run=args.dry_run,
    )
    uninstaller.detach_clients = bool(args.detach_clients)
    uninstaller.detach_managed_servers = bool(args.detach_managed_servers)
    uninstaller.detach_suite_tools = bool(args.detach_suite_tools)
    uninstaller.remove_path_block = bool(args.remove_path_block)
    uninstaller.remove_wrappers = bool(args.remove_wrappers)
    rc = uninstaller.run()
    if devlog_path:
        _write_devlog(devlog_path, "end", {"rc": rc if rc is not None else 0})
    raise SystemExit(rc if isinstance(rc, int) else 0)

if __name__ == "__main__":
    main()

# Backwards-compatible alias for older imports/tests.
SheshaUninstaller = NexusUninstaller
