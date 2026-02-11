import os
import json
import datetime
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

def _is_tty() -> bool:
    try:
        return bool(sys.stdout.isatty() or sys.stderr.isatty())
    except Exception:
        return False

def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd: Optional[int] = None
    tmp_path: Optional[Path] = None
    try:
        tmp_fd, tmp_path_str = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        tmp_path = Path(tmp_path_str)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            tmp_fd = None
            json.dump(payload, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except Exception:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

def _append_warning(project_root: Path, message: str) -> None:
    try:
        log_path = project_root / ".librarian" / "verify-warnings.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except Exception:
        return

class SheshaVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.manifest_path = self.project_root / ".librarian" / "manifest.json"

    def generate_report(self):
        if not self.manifest_path.exists():
            if _is_tty():
                print("No installation manifest found. Run install.py first.", file=sys.stderr)
            return

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception:
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup = self.manifest_path.with_suffix(f".json.corrupt.{stamp}")
            try:
                self.manifest_path.replace(backup)
                _append_warning(self.project_root, f"Recovered malformed manifest (backup: {backup})")
            except Exception:
                pass
            # Ensure future runs don't keep tripping over malformed JSON.
            recovered = {
                "install_date": None,
                "install_artifacts": [],
                "audit_snapshot": {},
                "version": "recovered",
            }
            try:
                _atomic_write_json(self.manifest_path, recovered)
            except Exception:
                pass
            if _is_tty():
                print("Manifest was malformed; it was recovered. Re-run install.py to regenerate a full manifest.", file=sys.stderr)
            return

        before = manifest.get("audit_snapshot", {})
        
        # Capture "After" state
        from audit import EnvironmentAuditor
        auditor = EnvironmentAuditor(self.project_root)
        after_audit = auditor.audit()
        
        print("\n" + "="*60)
        print("INSTALLATION VERIFICATION REPORT".center(60))
        print("="*60)
        
        print(f"\nInstall Date: {manifest.get('install_date')}")
        print(f"Project Root: {self.project_root}")
        
        print("\nBINARIES:")
        print(f"  Node: {'[ADDED]' if not before.get('node_present') and after_audit.node_present else 'Present' if after_audit.node_present else 'Missing'}")
        print(f"  NPM:  {'[ADDED]' if not before.get('npm_present') and after_audit.npm_present else 'Present' if after_audit.npm_present else 'Missing'}")
        print(f"  Docker: {'[RUNNING]' if after_audit.docker_running else '[NOT RUNNING]' if after_audit.docker_present else 'Missing'}")

        print("\nARTIFACTS CREATED:")
        for artifact in manifest.get("install_artifacts", []):
            status = "[VERIFIED]" if Path(artifact).exists() else "[MISSING]"
            print(f"  {status} {artifact}")

        print("\nPATH CHANGES:")
        before_path = set(before.get("path_entries", []))
        after_path = set(after_audit.path_entries)
        new_entries = after_path - before_path
        if new_entries:
            for entry in new_entries:
                print(f"  [+] {entry}")
        else:
            print("  No PATH changes detected.")

        print("="*60 + "\n")

if __name__ == "__main__":
    root = Path(__file__).parent.parent.resolve()
    verifier = SheshaVerifier(root)
    verifier.generate_report()
