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

def get_mcp_tools_home():
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

class SheshaUninstaller:
    def __init__(self, project_root: Path, kill_venv: bool = False, purge_data: bool = False):
        self.project_root = project_root
        self.kill_venv = kill_venv
        self.purge_data = purge_data
        self.manifest_path = self.project_root / ".librarian" / "manifest.json"

    def log(self, msg: str):
        print(f"[-] {msg}")

    def run(self):
        if not self.manifest_path.exists():
            print(f"⚠️  No installation manifest found at {self.manifest_path}.")
            print("   Proceeding with directory clean-up mode (fallback).")
            manifest = {}
        else:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)

        # Remove MCP attachments first (if any)
        if "attached_clients" in manifest:
            self.remove_mcp_attachments(manifest["attached_clients"])

        artifacts = manifest.get("install_artifacts", [])
        if artifacts:
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
    parser = argparse.ArgumentParser(description="Shesha Clean Room Uninstaller")
    parser.add_argument("--kill-venv", action="store_true", help="Remove the virtual environment as well")
    parser.add_argument("--purge-data", action="store_true", help="Force remove shared Nexus data (~/.mcp-tools)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent.resolve()
    uninstaller = SheshaUninstaller(root, kill_venv=args.kill_venv, purge_data=args.purge_data)
    uninstaller.run()

if __name__ == "__main__":
    main()
