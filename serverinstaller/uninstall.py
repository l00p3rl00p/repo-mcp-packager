import os
import shutil
import json
import argparse
import sys
import datetime
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


class NexusUninstaller:
    def __init__(
        self,
        project_root: Path,
        kill_venv: bool = False,
        purge_data: bool = False,
        verbose: bool = False,
        devlog: Optional[Path] = None,
        yes: bool = False,
        dry_run: bool = False,
    ):
        self.project_root = project_root
        self.kill_venv = kill_venv
        self.purge_data = purge_data
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

        if not self.manifest_path.exists():
            print(f"⚠️  No installation manifest found at {self.manifest_path}.")
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

        # Central suite cleanup:
        # - If --kill-venv is set: delete ~/.mcp-tools entirely (includes .venv)
        # - If --kill-venv is NOT set: delete everything under ~/.mcp-tools EXCEPT .venv
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

                if venv.exists():
                    targets.append(("dir", venv, "kept: nexus venv (~/.mcp-tools/.venv)"))

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

        print("\n🧹 Nexus Uninstall (Central-Only)")
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

        # Confirmation rules:
        # - --purge-data always requires confirmation
        # - --kill-venv is explained as the “destroy environments” flag
        if deduped:
            print()
            if not self.kill_venv:
                print("ℹ️  --kill-venv not set: preserving ~/.mcp-tools/.venv (if present).")
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

        # Remove PATH block if we are purging.
        _remove_path_block(verbose=self.verbose, devlog=self.devlog)
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
                print(f"⚠️  Failed to remove {path}: {e}")
                if self.devlog:
                    _write_devlog(self.devlog, "remove_failed", {"path": str(path), "error": str(e), "reason": reason})

        self.log("Uninstall complete (central-only).")
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
            self.log(f"ℹ️  Keeping shared Nexus ({remaining} tools detected).")
        elif remaining == 1:
            # Often the last folder is just an empty shell or a config file
            # Let's ask the user
            print(f"\n⚠️  You seem to be the last tool standing.")
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
            self.log("⚠️  MCP removal not available. Skipping IDE config cleanup.")
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
        verbose=args.verbose,
        devlog=devlog_path,
        yes=args.yes,
        dry_run=args.dry_run,
    )
    rc = uninstaller.run()
    if devlog_path:
        _write_devlog(devlog_path, "end", {"rc": rc if rc is not None else 0})
    raise SystemExit(rc if isinstance(rc, int) else 0)

if __name__ == "__main__":
    main()

# Backwards-compatible alias for older imports/tests.
SheshaUninstaller = NexusUninstaller
