import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any

class SheshaVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.manifest_path = self.project_root / ".librarian" / "manifest.json"

    def generate_report(self):
        if not self.manifest_path.exists():
            print("No installation manifest found. Run install.py first.")
            return

        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception:
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup = self.manifest_path.with_suffix(f".json.corrupt.{stamp}")
            try:
                self.manifest_path.replace(backup)
                print(f"Recovered malformed manifest. Backup: {backup}")
            except Exception:
                pass
            print("Manifest was malformed; run install.py again to regenerate it.")
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
