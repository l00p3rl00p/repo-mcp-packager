import os
import shutil
import json
import argparse
import sys
from pathlib import Path
from typing import List

# Import attach module for MCP removal
try:
    sys.path.append(str(Path(__file__).parent))
    from attach import remove_from_clients
    MCP_REMOVAL_AVAILABLE = True
except ImportError:
    MCP_REMOVAL_AVAILABLE = False

class SheshaUninstaller:
    def __init__(self, project_root: Path, kill_venv: bool = False):
        self.project_root = project_root
        self.kill_venv = kill_venv
        self.manifest_path = self.project_root / ".librarian" / "manifest.json"

    def log(self, msg: str):
        print(f"[-] {msg}")

    def run(self):
        if not self.manifest_path.exists():
            print(f"No installation manifest found at {self.manifest_path}. Aborting.")
            return

        with open(self.manifest_path, 'r') as f:
            manifest = json.load(f)

        # Remove MCP attachments first (if any)
        if "attached_clients" in manifest:
            self.remove_mcp_attachments(manifest["attached_clients"])

        artifacts = manifest.get("install_artifacts", [])
        self.log(f"Found {len(artifacts)} tracked artifacts for removal.")

        # 1. Remove tracked artifacts (files/dirs or surgical blocks)
        marker_start = "# Shesha Block START"
        marker_end = "# Shesha Block END"

        for path_str in artifacts:
            path = Path(path_str)
            if not path.exists():
                continue

            # Check for surgical markers in ANY file
            is_surgical = False
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    if marker_start in content:
                        is_surgical = True
                except Exception:
                    pass

            if is_surgical:
                self.log(f"Surgically reversing environment changes in: {path}")
                lines = path.read_text(encoding="utf-8").splitlines()
                new_lines = []
                inside_block = False
                for line in lines:
                    if line.strip() == marker_start:
                        inside_block = True
                        continue
                    if line.strip() == marker_end:
                        inside_block = False
                        continue
                    if not inside_block:
                        new_lines.append(line)
                
                path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                continue

            # Standard removal for directories/files
            if path.is_dir():
                self.log(f"Removing directory: {path}")
                shutil.rmtree(path, ignore_errors=True)
            else:
                self.log(f"Removing file: {path}")
                path.unlink(missing_ok=True)

        # 2. Cleanup manifest directory
        manifest_dir = self.manifest_path.parent
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
    parser = argparse.ArgumentParser(description="Shesha Clean Room Uninstaller")
    parser.add_argument("--kill-venv", action="store_true", help="Remove the virtual environment as well")
    args = parser.parse_args()

    root = Path(__file__).parent.parent.resolve()
    uninstaller = SheshaUninstaller(root, kill_venv=args.kill_venv)
    uninstaller.run()

if __name__ == "__main__":
    main()
