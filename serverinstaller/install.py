import os
from dataclasses import asdict
import sys
import argparse
import json
import datetime
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

__version__ = "3.1.0"

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

# Forge imports (Phase 12 Synergy)
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "forge"))
    from forge_engine import ForgeEngine
    FORGE_AVAILABLE = True
except ImportError:
    FORGE_AVAILABLE = False

GLOBAL_CONFIG_KEY = \"ide_config_paths\"


def get_global_config_path():
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools" / "config.json"
    return Path.home() / ".mcp-tools" / "config.json"

def get_global_ide_paths() -> Dict[str, str]:
    """Retrieve IDE paths from Nexus config"""
    config_path = get_global_config_path()
    try:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
            except json.JSONDecodeError:
                stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                backup = config_path.with_suffix(f".json.corrupt.{stamp}")
                config_path.replace(backup)
                try:
                    if sys.stdout.isatty() or sys.stderr.isatty():
                        print(f"Recovered malformed global config: {backup}", file=sys.stderr)
                except Exception:
                    pass
                return {}
            if not isinstance(data, dict):
                return {}
            ide_paths = data.get(GLOBAL_CONFIG_KEY, {})
            return ide_paths if isinstance(ide_paths, dict) else {}
    except Exception:
        pass
    return {}

def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """
    Write JSON atomically to avoid leaving a truncated / malformed file.
    """
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

class SheshaInstaller:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.portable_root = Path(__file__).parent.resolve()
        self.project_root = self.portable_root.parent.resolve()
        
        # Determine suite root for Forge synergy
        self.suite_root = self.project_root.parent # /repo-mcp-packager -> /mcp-creater-manager
        
        # Initialize components
        self.auditor = Auditor(self.project_root)
        self.artifacts = []
        self.mcp_attachments = []
    def ensure_executable(self, path: Path):
        """Universal Safety: Ensure scripts are executable."""
        if not path.exists() or not path.is_file(): return
        try:
            path.chmod(path.stat().st_mode | 0o111)
        except Exception as e:
            self.log(f"⚠️  Failed to set executable on {path.name}: {e}")

    def register_artifact(self, path: str, executable: bool = False):
        """Track artifacts for rollback and ensure permissions."""
        p = Path(path)
        if p not in self.artifacts:
            self.artifacts.append(p)
            if executable:
                self.ensure_executable(p)
        if not self.args.headless:
            print(f"[*] Registered artifact: {p}")

    def log(self, msg: str):
        """Print human logs and mirror structured logs for GUI."""
        if not self.args.headless:
            print(f"[*] {msg}")
        self.machine_log("log", msg)

    def error(self, msg: str, category: str = "runtime"):
        """Log error to console and machine-readable logs, then ROLLBACK."""
        print(f"[!] ERROR: {msg}", file=sys.stderr)
        self.machine_log("error", msg, {"category": category})
        self.rollback() # Safe exit
        sys.exit(1)

    def pre_flight_checks(self):
        """Verifies integrity and permissions before starting."""
        self.log("Running pre-flight checks...")
        try:
            # 1. Permission Check
            test_file = self.project_root / ".shesha_write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            # 2. Disk Space (Simple check for > 100MB)
            if hasattr(os, 'statvfs'):
                st = os.statvfs(self.project_root)
                free = (st.f_bavail * st.f_frsize) / (1024 * 1024)
                if free < 100:
                    self.log(f"⚠️  Low disk space: {free:.1f}MB remaining.")
            
            self.log("✅ Pre-flight checks passed.")
            return True
        except Exception as e:
            self.error(f"Pre-flight checks failed (Permissions/IO): {e}")
            return False

    def rollback(self):
        """Surgically remove all artifacts created during this run."""
        if not self.artifacts:
            return
            
        self.log(f"🔄 ROLLBACK: Removing {len(self.artifacts)} partial artifacts...")
        for art in reversed(self.artifacts):
            path = Path(art)
            if path.exists():
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    self.log(f"  🗑️ Removed: {path.name}")
                except Exception as e:
                    self.log(f"  ⚠️ Failed to remove {path.name}: {e}")
        self.log("✅ Rollback complete.")

    def machine_log(self, event: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Emit structured JSON for GUI consumption."""
        if not self.args.headless and not self.args.machine:
            return
            
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "level": "info" if event != "error" else "error",
            "event": event,
            "message": message,
            "data": data or {}
        }
        # If machine flag is set, print to stdout (or a specific log file if we had one)
        if self.args.machine:
            print(f"JSON_LOG:{json.dumps(log_entry)}")

    def resolve_entry_point(self) -> Optional[Path]:
        """Intelligently find and harden the main entry point."""
        py_files = [f for f in self.project_root.glob("*.py") if f.name not in ["install.py", "uninstall.py", "audit.py", "verify.py"]]
        sh_files = list(self.project_root.glob("*.sh"))
        
        candidates = sh_files + py_files
        if not candidates:
            return None
        
        if len(candidates) == 1:
            self.ensure_executable(candidates[0])
            return candidates[0]
            
        self.log("\n🔍 Multiple entry points detected:")
        for i, c in enumerate(candidates, 1):
            rec = " (Recommended)" if c.suffix == ".sh" else ""
            self.log(f"  {i}. {c.name}{rec}")
            
        if self.args.headless:
            # Default to first .sh or first .py
            best = sh_files[0] if sh_files else py_files[0]
            self.log(f"Headless Mode: Defaulting to {best.name}")
            self.ensure_executable(best)
            return best
            
        choice = input(f"\nSelect entry point [1-{len(candidates)}]: ").strip()
        try:
            selected = candidates[int(choice) - 1]
            self.ensure_executable(selected)
            return selected
        except:
            self.log("Invalid selection. Defaulting to first candidate.")
            self.ensure_executable(candidates[0])
            return candidates[0]

    def discover_project(self) -> Dict[str, Any]:
        """Scan the project root to see what application files are present."""
        self.log(f"Scanning project root: {self.project_root}")
        
        discovery = {
            "python_project": (self.project_root / "pyproject.toml").exists(),
            "npm_project": (self.project_root / "package.json").exists(),
            "gui_project": (self.project_root / "gui" / "package.json").exists(),
            "docker_project": (self.project_root / "Dockerfile").exists() or 
                             (self.project_root / "src" / "shesha" / "sandbox" / "Dockerfile").exists(),
            "python_requirements": (self.project_root / "requirements.txt").exists(),
            "python_setup": (self.project_root / "setup.py").exists(),
            "simple_script": False,
            "script_path": None,
        }
        
        # Check if this is a simple script (no deps, single or selectable .py/.sh files)
        if not discovery["python_project"] and not discovery["npm_project"]:
            script_file = self.resolve_entry_point()
            if script_file:
                discovery["simple_script"] = True
                discovery["script_path"] = script_file
                self.register_artifact(script_file, executable=True)
        
        self.log(f"Discovered: {', '.join([k for k, v in discovery.items() if v and k not in ['script_path']])} ")
        return discovery

    def setup_venv(self):
        """Ensure we are in or create a virtual environment."""
        if sys.prefix != sys.base_prefix:
            self.log("Already running in a virtual environment.")
            # We are already in a venv, no need to create or activate
            return

        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            self.log("Creating virtual environment...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_path)],
                    check=True,
                    timeout=60,  # 1 minute timeout for venv creation
                    capture_output=True,
                    text=True
                )
                self.log(f"Virtual environment created at {venv_path}")
                self.register_artifact(venv_path)
            except subprocess.TimeoutExpired:
                self.error("Timeout: Virtual environment creation took longer than 1 minute.")
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                self.error(f"Failed to create virtual environment: {e.stderr}")
                self.error("Hint: Ensure Python venv module is available and your system has enough resources.")
                sys.exit(1)
        else:
            self.log(f"Virtual environment already exists at {venv_path}")
        
        self.log(f"Virtual environment ready. Please activate it before continuing.")
        if not self.args.headless:
            self.log(f"Command: source {venv_path}/bin/activate")

    def install_python_deps(self, discovery: Dict[str, Any]):
        if discovery.get("has_requirements"):
            self.log("Installing Python dependencies from requirements.txt...")
            pip_path = self.project_root / ".venv" / "bin" / "pip"
            if pip_path.exists():
                cmd = [str(pip_path), "install", "-r", "requirements.txt"]
            else:
                cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            try:
                subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for pip install
                )
                self.log("Python dependencies installed successfully.")
            except subprocess.TimeoutExpired:
                self.error("Timeout: pip install took longer than 5 minutes")
                self.error("Hint: Check your network connection or try again")
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                self.error(f"Failed to install Python dependencies: {e.stderr}")
                self.error("Hint: Check requirements.txt for invalid packages")
                sys.exit(1)

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
            subprocess.run(
                ["npm", "install"],
                cwd=gui_path,
                check=True,
                timeout=300,  # 5 minute timeout for npm install
                capture_output=True,
                text=True
            )
            self.register_artifact(gui_path / "node_modules")
            self.log("npm dependencies installed successfully.")
        except subprocess.TimeoutExpired:
            self.error("Timeout: npm install took longer than 5 minutes")
            self.error("Hint: Check your network connection or try again")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            self.error(f"Failed to install npm dependencies: {e.stderr}")
            self.error("Hint: Check package.json for invalid packages")
            sys.exit(1)
        except FileNotFoundError:
            self.error("npm not found. Please install Node.js and npm")
            self.error("Install: brew install node (macOS) or apt-get install nodejs npm (Linux)")
            sys.exit(1)

    def write_manifest(self, audit: Dict[str, Any]):
        manifest_dir = self.project_root / ".librarian"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.json"
        
        # Detect remote URL if it's a git repo
        remote_url = None
        try:
            remote_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.project_root, text=True
            ).strip()
        except:
            pass

        manifest_data = {
            "install_date": audit["timestamp"],
            "install_artifacts": [str(p) for p in self.artifacts],
            "install_mode": "managed" if self.args.managed else "dev",
            "remote_url": remote_url,
            "audit_snapshot": audit,
            "version": "0.5.0-portable"
        }
        
        # Add MCP attachments if any
        if hasattr(self, 'mcp_attachments') and self.mcp_attachments:
            manifest_data["attached_clients"] = self.mcp_attachments

        _atomic_write_json(manifest_path, manifest_data)
        
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
        self.register_artifact(install_sh, executable=True)
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

            _atomic_write_json(manifest_path, manifest_data)
            
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
                self.register_artifact(bridge_path, executable=True)
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
            
            # Merge global config paths if available
            ide_paths = get_global_ide_paths()
            
            results = attach_to_clients(
                server_config,
                client_names=client_list,
                interactive=not self.args.headless,
                custom_paths=ide_paths
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
        if not getattr(self.args, "add_venv_to_path", False):
            return
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
        
        # Check if already in PATH
        if rc_file.exists() and export_line in rc_file.read_text():
            return

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
        
        self.register_artifact(rc_file) # Track that we modified this file
        self.log(f"Added to PATH in {rc_file}")

    def update(self):
        """Update the existing installation."""
        self.log(f"Checking for updates in {self.project_root}...")
        self.machine_log("update_start", "Starting update process", {"root": str(self.project_root)})
        
        # 1. Verify this is a git repo
        if not (self.project_root / ".git").exists():
            self.error("This project is not a git repository. Cannot auto-update.", "validation")
            
        # 2. Check for local changes
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.project_root, capture_output=True, text=True)
        if status.stdout.strip():
            self.log("⚠️  Local changes detected.")
            if not self.args.headless:
                choice = input("Update might overwrite changes. Force update anyway? [y/N]: ").strip().lower()
                if choice != 'y':
                    self.machine_log("update_aborted", "Update cancelled due to local changes")
                    self.log("Update aborted.")
                    return
        
        # 3. Perform the pull
        self.log("Pulling latest changes...")
        try:
            subprocess.run(["git", "pull"], cwd=self.project_root, check=True, capture_output=True, text=True)
            self.log("✅ Code updated successfully.")
            self.machine_log("git_pull_success", "Code synchronized with remote")
        except subprocess.CalledProcessError as e:
            self.error(f"Git Pull Failed: {e.stderr}", "network")

        # 4. Check for library-engine updates
        engine_dir = self.project_root / "mcp-link-library"
        if engine_dir.exists() and (engine_dir / ".git").exists():
            self.log(f"Update detected for child engine: {engine_dir.name}")
            try:
                subprocess.run(["git", "pull"], cwd=engine_dir, check=True, capture_output=True, text=True)
                self.machine_log("engine_update_success", "Library engine updated")
            except subprocess.CalledProcessError as e:
                self.machine_log("engine_update_fail", f"Engine update failed: {e.stderr}")
            
        # 5. Refresh dependencies
        discovery = self.discover_project()
        try:
            if discovery["python_project"]:
                self.install_python_deps(discovery)
                self.machine_log("deps_refresh", "Python dependencies refreshed")
            if discovery["gui_project"]:
                self.setup_npm(discovery)
                self.machine_log("deps_refresh", "NPM dependencies refreshed")
        except Exception as e:
            self.error(f"Dependency refresh failed: {str(e)}", "runtime")
            
        self.log("✨ All components refreshed and up to date.")
        self.machine_log("update_complete", "Update finished successfully")

    def handle_knowledge_base(self, discovery: Dict[str, Any]):
        """Offer to install the Knowledge Base (Librarian) for any project type."""
        engine_dir = self.project_root / "mcp-link-library"
        
        # If already exists, just update/bootstrap quietly if requested
        if engine_dir.exists():
            self.log(f"Knowledge Base found at {engine_dir.name}")
            return True
            
        print(f"\n[*] Installing Knowledge Base (mcp-link-library)...")
        try:
            subprocess.run(
                ["git", "clone", "https://github.com/l00p3rl00p/mcp-link-library", str(engine_dir)],
                check=True
            )
        except Exception as e:
            self.error(f"Failed to clone link library: {e}")
            return False
            
        # Run bootstrap
        engine_installer = engine_dir / "bootstrap.py"
        if not engine_installer.exists():
            engine_installer = engine_dir / "install.py"
        
        if engine_installer.exists():
            print(f"[*] Bootstrapping Knowledge Base...")
            cmd = [sys.executable, str(engine_installer)]
            # If we know what IDEs to attach to, pass them along
            if self.args.attach_to:
                cmd.extend(["--attach-to"] + self.args.attach_to)
            
            subprocess.run(cmd, cwd=engine_dir, check=True)
            self.register_artifact(engine_dir)
            return True
        return False

    def run(self):
        if self.args.update:
            self.update()
            return

        # Phase 12: Forge Loop
        if FORGE_AVAILABLE and (self.args.forge or self.args.forge_repo):
            engine = ForgeEngine(self.suite_root)
            source = self.args.forge_repo if self.args.forge_repo else self.args.forge
            self.log(f"🚀 FORGING: {source}")
            target = engine.forge(source, self.args.name)
            self.log(f"✅ FORGE COMPLETE: {target}")
            # After forge, we might want to continue installation in the new target
            self.project_root = target
            # Re-initialize auditor for the new target
            from audit import Auditor
            self.auditor = Auditor(self.project_root)

        if not self.args.headless and not sys.stdin.isatty():
            self.error("Interactive mode requires a TTY. Use --headless for automated install.")

        # 0. Pre-flight
        self.pre_flight_checks()
        
        try:
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
            
            # Handle "documents only" projects
            is_code_project = any([
                discovery["python_project"],
                discovery["npm_project"],
                discovery["gui_project"],
                discovery["docker_project"],
                discovery["python_requirements"],
                discovery["python_setup"]
            ])

            if not is_code_project and not self.args.generate_bridge:
                print("\n" + "!"*50)
                print("📎 DISCOVERY: DOCUMENTS & FOLDERS")
                print("!"*50)
                print("\nSeems this is just documents or folders.")
                print("There are no standard project files (no package.json, pyproject.toml, etc.)")
                print("detected, so there is nothing to automate or 'install' by default.")
                print("\nBUT: I can turn this directory into a searchable MCP Knowledge Base")
                print("by pulling down and configuring the 'mcp-link-library' for you.")
                
                if not self.args.headless:
                    print("Options:")
                    print("  [y] Yes, set up MCP server (clones mcp-link-library)")
                    print("  [n] No, keep as-is")
                    print("  [q] Abort installation")
                    
                    choice = input("\nChoice [y/n/q]: ").strip().lower()
                    
                    if choice in ['q', 'n']:
                        print("\n❎ Skipping setup. You can always use the library later:")
                        print("   👉 https://github.com/l00p3rl00p/mcp-link-library\n")
                        sys.exit(0)
                    
                    if choice == 'y':
                        engine_dir = self.project_root / "mcp-link-library"
                        if engine_dir.exists():
                            print(f"[*] Engine directory {engine_dir.name} already exists. Skipping clone.")
                        else:
                            print(f"[*] Pulling mcp-link-library into {engine_dir.name}...")
                            try:
                                subprocess.run(
                                    ["git", "clone", "https://github.com/l00p3rl00p/mcp-link-library", str(engine_dir)],
                                    check=True
                                )
                            except Exception as e:
                                self.error(f"Failed to clone link library: {e}")
                        
                        engine_installer = engine_dir / "bootstrap.py"
                        if not engine_installer.exists():
                            engine_installer = engine_dir / "install.py"
                        
                        if engine_installer.exists():
                            print(f"[*] Bootstrapping the new engine...")
                            cmd = [sys.executable, str(engine_installer)]
                            if self.args.attach_to:
                                cmd.extend(["--attach-to"] + self.args.attach_to)
                            
                            subprocess.run(cmd, cwd=engine_dir)
                            print("\n✅ Knowledge Base setup complete!")
                            sys.exit(0)
                        else:
                            self.error("Found the engine but couldn't find its installer (bootstrap.py or install.py).")
                    else:
                        print("\n❎ Skipping setup. Use https://github.com/l00p3rl00p/mcp-link-library manually if needed.")
                        sys.exit(0)
                else:
                    self.log("Headless mode: Skipping auto-scaffold to avoid side-effects. Use manually.")
                    sys.exit(0)

            install_choices = {
                "python": discovery["python_project"],
                "gui": discovery["gui_project"] and not self.args.no_gui,
                "knowledge_base": False,
            }

            if not self.args.headless:
                print("\n" + "="*40)
                print("COMPONENT INVENTORY".center(40))
                print("="*40)
                print(" (Enter 'q' at any prompt to abort)")
                print("-" * 40)
                
                if discovery["python_project"]:
                    choice = input("Install Python Server/CLI? [Y/n/q]: ").strip().lower()
                    if choice == 'q':
                        sys.exit(0)
                    install_choices["python"] = choice != 'n'
                
                if discovery["gui_project"]:
                    choice = input("Install GUI Frontend? [Y/n/q]: ").strip().lower()
                    if choice == 'q':
                        sys.exit(0)
                    install_choices["gui"] = choice != 'n'
                
                choice = input("Install Knowledge Base (Librarian)? [Y/n/q]: ").strip().lower()
                if choice == 'q':
                    sys.exit(0)
                install_choices["knowledge_base"] = choice != 'n'

                if not any(install_choices.values()):
                    print("\nNo components selected for installation.")
                    if input("Exit now? [Y/n]: ").strip().lower() != 'n':
                        sys.exit(0)
                    
                print("="*40 + "\n")

            if install_choices["python"]:
                self.setup_venv()
                self.install_python_deps(discovery)
            
            if install_choices.get("knowledge_base"):
                self.handle_knowledge_base(discovery)
                
            if install_choices["gui"]:
                self.setup_npm(discovery)
            
            if self.args.generate_bridge or self.args.attach_to:
                self.handle_mcp_bridge(discovery)
            
            audit_dict = asdict(audit) if hasattr(audit, '__dict__') else audit
            if install_choices["python"]:
                self.setup_path(audit_dict)
            
            self.write_manifest(audit_dict)
            self.log("Installation complete.")
        except Exception:
            self.rollback()
            raise

def main():
    parser = argparse.ArgumentParser(description="Shesha Clean Room Installer")
    parser.add_argument("--headless", action="store_true", help="Non-interactive install")
    parser.add_argument("--no-gui", action="store_true", help="Skip GUI installation")
    parser.add_argument("--npm-policy", choices=["local", "global", "auto"], default="auto")
    parser.add_argument("--docker-policy", choices=["fail", "skip"], default="skip")
    parser.add_argument("--storage-path", type=Path)
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--machine", action="store_true", help="Emit machine-readable JSON logs to stdout")
    parser.add_argument("--managed", action="store_true", help="Install into managed library folder")
    parser.add_argument("--update", action="store_true", help="Update the existing server installation")
    parser.add_argument("--add-venv-to-path", action="store_true", dest="add_venv_to_path", help="Opt-in: add this repo's .venv/bin to your shell PATH (edits ~/.zshrc or ~/.bashrc)")
    
    # MCP Bridge arguments
    parser.add_argument("--generate-bridge", action="store_true", help="Generate MCP wrapper for legacy code")
    parser.add_argument("--attach-to", nargs="+", 
                       choices=["all", "claude", "xcode", "cursor", "codex", "aistudio", "vscode"],
                       help="Attach MCP server to IDE(s)")

    # Forge arguments (The Factory Release)
    parser.add_argument("--forge", type=str, help="Forge a local directory into an MCP server")
    parser.add_argument("--forge-repo", type=str, help="Forge a remote repository into an MCP server")
    parser.add_argument("--name", type=str, help="Optional name for the forged server")
    
    args = parser.parse_args()

    
    # Manual helper for asdict if needed
    from audit import AuditResult
    import dataclasses
    
    installer = SheshaInstaller(args)
    installer.run()

if __name__ == "__main__":
    main()
