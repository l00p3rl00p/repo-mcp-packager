import os
from dataclasses import asdict
import sys
import argparse
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ensure we can import from the same directory
sys.path.append(str(Path(__file__).parent))
from audit import EnvironmentAuditor

# MCP Bridge imports (optional)
try:
    from bridge import MCPBridgeGenerator
    from attach import attach_to_clients, detect_clients
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class SheshaInstaller:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.portable_root = Path(__file__).parent.resolve()
        self.project_root = self.portable_root.parent.resolve()
        self.auditor = EnvironmentAuditor(self.project_root)
        self.artifacts = []

    def log(self, msg: str):
        if not self.args.headless:
            print(f"[*] {msg}")

    def error(self, msg: str):
        print(f"[!] ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

    def discover_project(self) -> Dict[str, Any]:
        """Scan the project root to see what application files are present."""
        self.log(f"Scanning project root: {self.project_root}")
        
        discovery = {
            "python_project": (self.project_root / "pyproject.toml").exists(),
            "npm_project": (self.project_root / "package.json").exists(),
            "gui_project": (self.project_root / "gui" / "package.json").exists(),
            "docker_project": (self.project_root / "Dockerfile").exists() or 
                             (self.project_root / "src" / "shesha" / "sandbox" / "Dockerfile").exists(),
            "simple_script": False,
            "script_path": None,
        }
        
        # Check if this is a simple script (no deps, single .py file)
        if not discovery["python_project"] and not discovery["npm_project"]:
            py_files = list(self.project_root.glob("*.py"))
            if len(py_files) == 1:
                script_file = py_files[0]
                # Exclude installer scripts themselves
                if script_file.name not in ["install.py", "uninstall.py", "audit.py", "verify.py"]:
                    discovery["simple_script"] = True
                    discovery["script_path"] = script_file
        
        self.log(f"Discovered: {', '.join([k for k, v in discovery.items() if v and k not in ['script_path']])} ")
        return discovery

    def setup_venv(self):
        """Ensure we are in or create a virtual environment."""
        if sys.prefix != sys.base_prefix:
            self.log("Already running in a virtual environment.")
            return

        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            self.log(f"Creating virtual environment at {venv_path}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            self.artifacts.append(str(venv_path))
        
        self.log(f"Virtual environment ready. Please activate it before continuing.")
        if not self.args.headless:
            self.log(f"Command: source {venv_path}/bin/activate")

    def install_python_deps(self, discovery: Dict[str, Any]):
        if discovery["python_project"]:
            self.log("Installing Python dependencies (local source)...")
            cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
            if discovery["npm_project"]:
                cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
            try:
                subprocess.run(cmd, cwd=self.project_root, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                self.log(f"Warning: pip install failed. This is expected if external dependencies are missing or Python version is incompatible.")
                self.log(f"Error: {e.stderr}")

    def setup_npm(self, discovery: Dict[str, Any]):
        if not discovery["gui_project"]:
            return

        policy = self.args.npm_policy
        gui_path = self.project_root / "gui"
        
        if policy == "local":
            self.log("NPM Policy: Local isolation. (Note: implementation would use nodeenv here)")
            # Stub for nodeenv logic if available
        
        self.log(f"Running npm install in {gui_path}...")
        try:
            subprocess.run(["npm", "install"], cwd=gui_path, check=True)
            self.artifacts.append(str(gui_path / "node_modules"))
        except Exception as e:
            self.log(f"Warning: npm install failed: {e}")

    def write_manifest(self, audit: Dict[str, Any]):
        manifest_dir = self.project_root / ".librarian"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.json"
        
        manifest_data = {
            "install_date": audit["timestamp"],
            "install_artifacts": self.artifacts,
            "audit_snapshot": audit,
            "version": "0.5.0-portable"
        }
        
        # Add MCP attachments if any
        if hasattr(self, 'mcp_attachments') and self.mcp_attachments:
            manifest_data["attached_clients"] = self.mcp_attachments
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        self.log(f"Installation manifest written to {manifest_path}")

    def generate_shell_wrapper(self, script_path: Path):
        """Generate a lightweight install.sh for a simple script"""
        script_name = script_path.stem
        install_sh = self.project_root / "install.sh"
        
        wrapper_content = f"""#!/bin/bash
set -e

echo "🔧 Installing {script_name}..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found."
    echo "   Install Python  3.6+ to continue."
    exit 1
fi

# Make executable
chmod +x {script_path.name}
echo "✅ Made {script_path.name} executable"

# Installation options
echo ""
echo "Installation Options:"
echo "  1. Install to PATH (/usr/local/bin/{script_name})"
echo "  2. Use in current directory (./{script_path.name})"
echo ""
read -p "Choose [1/2]: " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    if [ -w /usr/local/bin ]; then
        cp {script_path.name} /usr/local/bin/{script_name}
        echo "✅ Installed to /usr/local/bin/{script_name}"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: {script_name} --help"
    else
        echo "⚠️  Need sudo for /usr/local/bin"
        sudo cp {script_path.name} /usr/local/bin/{script_name}
        echo "✅ Installed to /usr/local/bin/{script_name}"
        echo ""
        echo "🎉 Installation complete!"
        echo "   Try: {script_name} --help"
    fi
else
    echo "✅ Ready to use in current directory"
    echo ""
    echo "🎉 Installation complete!"
    echo "   Try: ./{script_path.name} --help"
fi
"""
        
        install_sh.write_text(wrapper_content)
        install_sh.chmod(0o755)
        self.log(f"Created install.sh wrapper at {install_sh}")
        return install_sh

    def handle_simple_script(self, discovery: Dict[str, Any]):
        """Handle simple single-file scripts with user choice"""
        script_path = discovery["script_path"]
        
        print(f"\n{'='*50}")
        print(f"📄 Detected Simple Script: {script_path.name}")
        print(f"{'='*50}\n")
        print("This looks like a standalone script (no pyproject.toml/dependencies).")
        print("")
        print("Options:")
        print("  1. Create install.sh wrapper (lightweight, recommended)")
        print("  2. Package as full Python project (generate pyproject.toml + .venv)")
        print("  3. Exit (leave as-is)")
        print("")
        
        if self.args.headless:
            choice = "1"  # Default to lightweight in headless mode
            self.log("Headless mode: defaulting to lightweight wrapper")
        else:
            choice = input("Choose [1/2/3]: ").strip()
        
        if choice == "1":
            # Lightweight wrapper
            wrapper_path = self.generate_shell_wrapper(script_path)
            print(f"\n✅ Created lightweight installer: {wrapper_path.name}")
            print(f"   Try: ./install.sh")
            
            # Write minimal manifest
            audit = self.auditor.audit()
            audit_dict = {
                "timestamp": audit.timestamp if hasattr(audit, 'timestamp') else str(audit),
                "shell": audit.shell if hasattr(audit, 'shell') else "unknown",
                "python_version": audit.python_version if hasattr(audit, 'python_version') else sys.version.split()[0],
            }
            
            manifest_dir = self.project_root / ".librarian"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = manifest_dir / "manifest.json"
            
            manifest_data = {
                "install_date": audit_dict["timestamp"],
                "install_type": "lightweight_wrapper",
                "script_file": str(script_path),
                "wrapper_file": str(wrapper_path),
                "version": "0.5.0-portable"
            }
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            
            self.log(f"Manifest written to {manifest_path}")
            
        elif choice == "2":
            # Full packaging (generate pyproject.toml and proceed normally)
            print("\n🔧 Generating pyproject.toml...")
            script_name = script_path.stem
            
            pyproject_content = f"""[project]
name = "{script_name}"
version = "0.1.0"
description = "Automatically generated package"
requires-python = ">=3.6"

[project.scripts]
{script_name} = "{script_name}:main"
"""
            
            pyproject_path = self.project_root / "pyproject.toml"
            pyproject_path.write_text(pyproject_content)
            print(f"✅ Created {pyproject_path}")
            
            # Re-discover and proceed with full install
            discovery = self.discover_project()
            self.setup_venv()
            self.install_python_deps(discovery)
            
            audit = self.auditor.audit()
            audit_dict = {
                "timestamp": audit.timestamp if hasattr(audit, 'timestamp') else str(audit),
                "shell": audit.shell if hasattr(audit, 'shell') else "unknown",
                "python_version": audit.python_version if hasattr(audit, 'python_version') else sys.version.split()[0],
            }
            self.write_manifest(audit_dict)
            print("\n✅ Full packaging complete!")
            
        else:
            # Exit / do nothing
            print("\n❎ Exiting. No changes made.")
            sys.exit(0)

    def handle_mcp_bridge(self, discovery: Dict[str, Any]):
        """
        Handle MCP bridge generation and IDE attachment.
        
        Logic:
        1. Check if project has/needs MCP server
        2. Generate bridge if requested
        3. Attach to IDEs if requested
        """
        if not MCP_AVAILABLE:
            self.log("⚠️  MCP bridge modules not available. Skipping MCP setup.")
            return
        
        server_config = None
        
        # Step 1: Detect or generate MCP server
        if self.args.generate_bridge:
            # Generate bridge for legacy code
            self.log("Generating MCP bridge for legacy code...")
            generator = MCPBridgeGenerator(self.project_root)
            bridge_path = generator.generate_bridge()
            
            if bridge_path:
                server_config = {
                    "name": self.project_root.name,
                    "command": "python",
                    "args": [str(bridge_path)]
                }
                self.artifacts.append(str(bridge_path))
        else:
            # Check if project already has an MCP server
            # Look for common patterns: mcp_server.py, librarian mcp, package.json with mcp script
            if (self.project_root / "mcp_server.py").exists():
                server_config = {
                    "name": self.project_root.name,
                    "command": "python",
                    "args": [str(self.project_root / "mcp_server.py")]
                }
            elif discovery.get("python_project") and (self.project_root / "src").exists():
                # Check for Shesha/Librarian MCP server
                librarian_mcp = self.project_root / "src" / "shesha" / "librarian" / "mcp.py"
                if librarian_mcp.exists():
                    server_config = {
                        "name": "shesha",
                        "command": str(self.project_root / ".venv" / "bin" / "librarian"),
                        "args": ["mcp", "run"]
                    }
            elif discovery.get("npm_project"):
                # Check package.json for MCP-related scripts
                pkg_json = self.project_root / "package.json"
                try:
                    pkg_data = json.loads(pkg_json.read_text())
                    # Common pattern: npx -y @package/name mcp
                    if pkg_data.get("name"):
                        server_config = {
                            "name": pkg_data["name"],
                            "command": "npx",
                            "args": ["-y", pkg_data["name"], "mcp"]
                        }
                except:
                    pass
        
        # Step 2: Attach to IDEs if requested
        if server_config and self.args.attach_to:
            client_list = None if "all" in self.args.attach_to else self.args.attach_to
            
            results = attach_to_clients(
                server_config,
                client_names=client_list,
                interactive=not self.args.headless
            )
            
            # Store attachment info in manifest
            if not hasattr(self, 'mcp_attachments'):
                self.mcp_attachments = []
            
            for result in results:
                if result.success:
                    self.mcp_attachments.append({
                        "name": result.client_name,
                        "config_path": str(result.config_path),
                        "server_key": result.server_name
                    })

    def setup_path(self, audit: Dict[str, Any]):
        """Offer to add Shesha to PATH with markers for surgical reversal."""
        if self.args.headless:
            return

        shell = audit.get("shell", "")
        rc_file = None
        if "zsh" in shell:
            rc_file = Path.home() / ".zshrc"
        elif "bash" in shell:
            rc_file = Path.home() / ".bashrc"

        if not rc_file or not rc_file.exists():
            return

        venv_bin = self.project_root / ".venv" / "bin"
        if sys.platform.startswith("win"):
            venv_bin = self.project_root / ".venv" / "Scripts"
        
        export_line = f'export PATH="{venv_bin.resolve()}:$PATH"'
        
        self.log(f"\nOptional: add Shesha to PATH so 'librarian' is available everywhere.")
        self.log(f"  This will modify: {rc_file}")
        self.log(f"  (Markers # Shesha Block START/END will be used for safe reversal)")
        
        choice = input("Add to PATH? [y/N]: ").strip().lower()
        if choice != "y":
            return

        marker_start = "# Shesha Block START"
        marker_end = "# Shesha Block END"
        
        block = f"\n{marker_start}\n{export_line}\n{marker_end}\n"
        
        with rc_file.open("a", encoding="utf-8") as handle:
            handle.write(block)
        
        self.artifacts.append(str(rc_file)) # Track that we modified this file
        self.log(f"Added to PATH in {rc_file}")

    def run(self):
        if not self.args.headless and not sys.stdin.isatty():
            self.error("Interactive mode requires a TTY. Use --headless for automated install.")

        audit = self.auditor.audit()
        
        # Hard requirement check
        py_major, py_minor = map(int, audit.python_version.split('.'))
        if (py_major, py_minor) < (3, 11):
            self.log(f"WARNING: Python {audit.python_version} detected. Most Shesha/MCP projects require 3.11+.")
            if self.args.docker_policy == "fail":
                self.error("Python version incompatible.")

        discovery = self.discover_project()
        
        # Handle simple scripts (Philosophy: not every repo is a product)
        if discovery["simple_script"]:
            self.handle_simple_script(discovery)
            return
        
        # Component Selection
        install_choices = {
            "python": discovery["python_project"],
            "gui": discovery["gui_project"] and not self.args.no_gui,
        }
        
        if not self.args.headless:
            print("\n" + "="*40)
            print("COMPONENT INVENTORY".center(40))
            print("="*40)
            
            if discovery["python_project"]:
                choice = input("Install Python Server/CLI? [Y/n]: ").strip().lower()
                install_choices["python"] = choice != 'n'
            
            if discovery["gui_project"]:
                choice = input("Install GUI Frontend? [Y/n]: ").strip().lower()
                install_choices["gui"] = choice != 'n'
            
            print("="*40 + "\n")

        if install_choices["python"]:
            self.setup_venv()
            self.install_python_deps(discovery)
        
        if install_choices["gui"]:
            self.setup_npm(discovery)
        
        # MCP Bridge handling (if requested)
        if self.args.generate_bridge or self.args.attach_to:
            self.handle_mcp_bridge(discovery)
        
        audit_dict = asdict(audit) if hasattr(audit, '__dict__') else audit
        if install_choices["python"]:
            self.setup_path(audit_dict)
        
        self.write_manifest(audit_dict)
        self.log("Installation complete.")

def main():
    parser = argparse.ArgumentParser(description="Shesha Clean Room Installer")
    parser.add_argument("--headless", action="store_true", help="Non-interactive install")
    parser.add_argument("--no-gui", action="store_true", help="Skip GUI installation")
    parser.add_argument("--npm-policy", choices=["local", "global", "auto"], default="auto")
    parser.add_argument("--docker-policy", choices=["fail", "skip"], default="skip")
    parser.add_argument("--storage-path", type=Path)
    parser.add_argument("--log-dir", type=Path)
    
    # MCP Bridge arguments
    parser.add_argument("--generate-bridge", action="store_true", help="Generate MCP wrapper for legacy code")
    parser.add_argument("--attach-to", nargs="+", 
                       choices=["all", "claude", "xcode", "cursor", "codex", "aistudio", "vscode"],
                       help="Attach MCP server to IDE(s)")
    
    args = parser.parse_args()
    
    # Manual helper for asdict if needed
    from audit import AuditResult
    import dataclasses
    
    installer = SheshaInstaller(args)
    installer.run()

if __name__ == "__main__":
    main()
