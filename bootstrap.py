import os, sys, shutil, platform, argparse, hashlib, subprocess
from pathlib import Path

# Track artifacts for universal rollback
INSTALLED_ARTIFACTS = []

def get_mcp_tools_home():
    if platform.system() == "Windows":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

def get_workspace_root():
    """Find workspace by looking for sibling repos."""
    current = Path(__file__).parent
    parent = current.parent
    siblings = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    found = [s for s in siblings if (parent / s).exists()]
    return parent if len(found) >= 2 else None

def detect_which_repo():
    return Path(__file__).parent.name

def detect_full_suite(workspace: Path):
    """Check if we are in a Workforce Nexus workspace (all 4 repos)."""
    required = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    missing = [r for r in required if not (workspace / r).exists()]
    return len(missing) == 0

def ask_convergence_tier():
    print("\n🔗 Nexus Application Convergence Detected!")
    print("="*50)
    print("You have the full suite detected. How would you like to configure the Nexus?")
    
    print(f"\n{'Tier':<12} | {'Area':<14} | {'Setup':<20}")
    print("-" * 60)
    print(f"{'Lite':<12} | {'Distributed':<14} | {'Workspace execution, Shared Config'}")
    print(f"{'Standard':<12} | {'Linked':<14} | {'Symlinks to ~/.mcp-tools/suite'}")
    print(f"{'Industrial':<12} | {'Unified':<14} | {'Managed Mirror in ~/.mcp-tools/app'}")
    print("-" * 60)
    
    choice = input("\nSelect Tier [l/s/I] (Default: Industrial): ").strip().lower()
    if choice == 'l': return 'lite'
    if choice == 's': return 'standard'
    return 'industrial'

def ask_user_install_strategy():
    print("\n🚀 MCP Tools Suite Bootstrap")
    print("="*50)
    print(f"Current repo: {detect_which_repo()}")
    print(f"Central install: {get_mcp_tools_home()}")
    
    print("\nReliability Tiers Decision Matrix:")
    print("-" * 80)
    print(f"{'Tier':<12} | {'Level':<12} | {'Strategy':<18} | {'Pros/Cons'}")
    print("-" * 80)
    print(f"{'Lite':<12} | {'Basic':<12} | {'Zero-Dep':<18} | {'👍 Portable, 👎 Basic matching'}")
    print(f"{'Standard':<12} | {'High':<12} | {'Pure Python':<18} | {'👍 Regex indexing, 👎 Manual venv'}")
    print(f"{'Industrial':<12} | {'Hardened':<12} | {'Infrastructure':<18} | {'👍 Maximum precision, 👎 Disk space'}")
    print("-" * 80)
    
    tier = 'industrial'
    t_choice = input("\nSelect Reliability Tier [l/s/I] (Default: Industrial): ").strip().lower()
    if t_choice == 'l': tier = 'lite'
    elif t_choice == 's': tier = 'standard'
    elif t_choice == 'i': tier = 'industrial'

    print("\nInstall strategy:")
    print("  [1] Full auto - Just do it all")
    print("  [2] Step by step - Ask each action")
    print("  [3] Manual - Exit")
    
    while True:
        choice = input("\nChoice [1/2/3]: ").strip()
        if choice in ['1','2','3']:
            return {'strategy': {'1':'full', '2':'step', '3':'manual'}[choice], 'tier': tier}



def ask(question):
    print(f"\n❓ {question}")
    while True:
        r = input("   [Y/n]: ").strip().lower()
        if r in ['y','yes','']: return True
        if r in ['n','no']: return False

def pre_flight_checks(central: Path):
    """Universal Safety: Verify integrity and permissions."""
    print(f"[*] Running pre-flight checks at {central}...")
    try:
        central.mkdir(parents=True, exist_ok=True)
        test_file = central / ".nexus_write_test"
        test_file.write_text("test")
        test_file.unlink()
        print("✅ Pre-flight checks passed.")
        return True
    except Exception as e:
        print(f"❌ Pre-flight checks failed: {e}")
        return False

def rollback():
    """Universal Safety: Multi-tool recovery."""
    if not INSTALLED_ARTIFACTS:
        return
    print(f"\n🔄 ROLLBACK: Removing {len(INSTALLED_ARTIFACTS)} partial installations...")
    for target in reversed(INSTALLED_ARTIFACTS):
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                print(f"  🗑️ Removed: {target.name}")
            except Exception as e:
                print(f"  ⚠️  Failed to remove {target.name}: {e}")
    print("✅ Rollback complete.")

def ensure_executable(path: Path):
    """Universal Safety: Ensure scripts are executable recursively."""
    if not path.exists(): return
    
    # Files to target specifically
    entry_points = ['mcp.py', 'mcp_injector.py', 'install.py', 'uninstall.py', 'mcp_server_manager.py', 'bootstrap.py']
    
    if path.is_file():
        if path.suffix == '.sh' or path.name in entry_points:
            try:
                path.chmod(path.stat().st_mode | 0o111)
                # print(f"  🔓 Executable: {path.name}") # Verbose
            except Exception as e:
                print(f"  ⚠️  Failed to set executable on {path.name}: {e}")
    elif path.is_dir():
        for item in path.iterdir():
            ensure_executable(item)

def install_to_central(central, workspace):
    central.mkdir(parents=True, exist_ok=True)
    
    # Define our components
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    for repo in repos:
        source = workspace / repo
        target = central / repo
        
        if not source.exists():
            print(f"⚠️  Skipping {repo}: Not found in workspace")
            continue
            
        if target.exists():
            # If target exists, we update it by removing and re-copying
            try:
                shutil.rmtree(target)
            except Exception as e:
                print(f"❌ Failed to remove existing {repo}: {e}")
                raise e # Trigger rollback
        
        try:
            # Ignore __pycache__, .git, .venv, node_modules to keep it clean
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.git', '.venv', 'node_modules', '.DS_Store'))
            INSTALLED_ARTIFACTS.append(target)
            
            # Phase 9: Permissions Hardening
            ensure_executable(target)
            
            print(f"✅ Installed {repo}")
        except Exception as e:
            print(f"❌ Failed to copy {repo}: {e}")
            raise e # Trigger rollback
            continue

        if repo == 'repo-mcp-packager':
            uninstall_src = target / "serverinstaller" / "uninstall.py"
            uninstall_dest = target / "uninstall.py"
            if uninstall_src.exists():
                try:
                    shutil.copy2(uninstall_src, uninstall_dest)
                    # Make executable
                    uninstall_dest.chmod(uninstall_dest.stat().st_mode | 0o111)
                except Exception as e:
                    print(f"⚠️  Failed to expose uninstall.py: {e}")

def install_converged_application(tier, workspace):
    """Phase 12: Application Convergence Logic."""
    central = get_mcp_tools_home()
    central.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 Deploying Nexus Application [Tier: {tier.upper()}]...")
    
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    
    if tier == 'lite':
        # Lite: Config pointers only. Logic handled by tools checking workspace.
        # We just create the root ensures configs can live there.
        print("✅ Lite mode: Workspace is authoritative. Config root created.")
        
    elif tier == 'standard':
        # Standard: Symlinks
        suite_dir = central / "suite"
        suite_dir.mkdir(parents=True, exist_ok=True)
        for repo in repos:
            src = workspace / repo
            dest = suite_dir / repo
            if dest.exists() or dest.is_symlink():
                if dest.is_dir() and not dest.is_symlink():
                    shutil.rmtree(dest) # Remove physical copy if switching to symlink
                else:
                    dest.unlink()
            os.symlink(src, dest)
            print(f"🔗 Linked {repo} -> {dest}")
            
    elif tier == 'industrial':
        # Industrial: Managed Mirror (Copy)
        # We reuse install_to_central logic but ensure global venv
        install_to_central(central, workspace)
        setup_nexus_venv(central)
        create_hardened_entry_points(central)
        ensure_global_path(central)
        # Trigger Librarian Synergy (Lazy sync)
        print("🧠 Triggering Librarian Suite Indexing...")
        subprocess.run([sys.executable, str(central / "mcp-link-library" / "mcp.py"), "--index-suite"], check=False)

    print(f"\n✨ Convergence Complete! Your Nexus is ready in {tier} mode.")

def setup_nexus_venv(central: Path):
    """Create a dedicated Nexus venv for --industrial mode."""
    venv_dir = central / ".venv"
    print(f"\n📦 Building Industrial Infrastructure at {venv_dir}...")
    
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        
        # Determine pip path
        if platform.system() == "Windows":
            pip = venv_dir / "Scripts" / "pip.exe"
        else:
            pip = venv_dir / "bin" / "pip"
            
        print("📥 Installing high-confidence libraries (pathspec, jsonschema)...")
        subprocess.run([str(pip), "install", "pathspec", "jsonschema"], check=True)
        print("✅ Nexus Venv ready.")
        return True
    except Exception as e:
        print(f"❌ Failed to setup Nexus Venv: {e}")
        return False

def ensure_global_path(central: Path):
    """Surgically add ~/.mcp-tools/bin to user PATH."""
    bin_dir = central / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Identify shell config
    shell = os.environ.get("SHELL", "")
    rc_file = None
    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"
    
    if not rc_file or not rc_file.exists():
        print(f"⚠️  Could not find shell config for {shell}. Please add {bin_dir} to your PATH manually.")
        return False

    export_line = f'export PATH="{bin_dir}:$PATH"'
    content = rc_file.read_text(errors='ignore')
    
    if export_line in content:
        print(f"✅ PATH already includes {bin_dir}")
        return True

    print(f"\n📎 Adding {bin_dir} to your global PATH...")
    marker_start = "# Workforce Nexus Block START"
    marker_end = "# Workforce Nexus Block END"
    
    # Check if a block already exists to avoid duplication
    if marker_start in content:
        print("⚠️  Workforce Nexus block already exists in shell config. Updating...")
        # (Simplified update: append if not found, advanced would replace block)
    
    block = f"\n{marker_start}\n{export_line}\n{marker_end}\n"
    try:
        with open(rc_file, "a") as f:
            f.write(block)
        print(f"✅ Success! Please restart your terminal or run: source {rc_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to update shell config: {e}")
        return False

def create_hardened_entry_points(central: Path):
    """Create venv-locked executable wrappers in bin/."""
    bin_dir = central / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    venv_python = central / ".venv" / "bin" / "python"
    if platform.system() == "Windows":
        venv_python = central / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        # Fallback to system python if venv failed, but warn
        print("⚠️  Hardened venv not found. Using system python for entry points.")
        venv_python = sys.executable

    # Command mapping: entry_name -> (repo_dir, module_name)
    commands = {
        "mcp-surgeon": ("mcp-injector", "mcp_injector.py"),
        "mcp-observer": ("mcp-server-manager", "mcp_server_manager.py"),
        "mcp-librarian": ("mcp-link-library", "mcp.py"),
        "mcp-activator": ("repo-mcp-packager", "bootstrap.py") # Bootstrap acts as activator
    }
    
    for cmd, (repo, module) in commands.items():
        cmd_path = bin_dir / cmd
        target_script = central / repo / module
        
        if not target_script.exists():
            continue
            
        # Write the hardened wrapper
        wrapper = f"""#!/bin/bash
# Workforce Nexus Hardened Wrapper
"{venv_python}" "{target_script}" "$@"
"""
        try:
            cmd_path.write_text(wrapper)
            cmd_path.chmod(cmd_path.stat().st_mode | 0o111)
            print(f"✅ Created hardened entry point: {cmd}")
        except Exception as e:
            print(f"❌ Failed to create entry point {cmd}: {e}")

def generate_integrity_manifest(central: Path):
    """Generate SHA-256 integrity manifest for all installed files."""
    print("\n🛡️  Generating Integrity Manifest...")
    manifest_file = central / "manifest.sha256"
    hashes = []
    
    for root, dirs, files in os.walk(central):
        if ".venv" in root or ".git" in root: continue
        
        for f in files:
            if f == "manifest.sha256": continue
            path = Path(root) / f
            try:
                rel_path = path.relative_to(central)
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.append(f"{sha}  {rel_path}")
            except:
                pass
                
    manifest_file.write_text("\n".join(hashes), encoding="utf-8")
    print(f"✅ Integrity locked at {manifest_file}")

def main():
    parser = argparse.ArgumentParser(description="Nexus Bootstrap - Tiered Reliability")
    parser.add_argument("--lite", action="store_true", help="Lite mode (Zero-Dep)")
    parser.add_argument("--industrial", action="store_true", help="Industrial mode (Infrastructure)")
    parser.add_argument("--sync", action="store_true", help="Sync Industrial Nexus from workspace (Update logic)")
    parser.add_argument("--strategy", choices=["full", "step"], help="Installation strategy")
    parser.add_argument("--gui", action="store_true", help="Launch GUI after installation")
    args = parser.parse_args()

    if args.sync:
        workspace = get_workspace_root()
        if not workspace:
            print("❌ Cannot find workspace to sync from.")
            sys.exit(1)
        print("🔄 Syncing Industrial Nexus from workspace...")
        install_converged_application('industrial', workspace)
        return

    if sys.version_info < (3,6):
        print("❌ Python 3.6+ required")
        sys.exit(1)
    
    
    workspace = get_workspace_root()
    if not workspace:
        print("❌ Cannot find workspace (need sibling repos)")
        sys.exit(1)
        
    # Phase 12: Convergence Check
    if detect_full_suite(workspace):
        if not args.lite and not args.industrial:
            # If no manual flags, prompt for convergence
            tier = ask_convergence_tier()
            install_converged_application(tier, workspace)
            return
            
    # Legacy/Single Repo Flow
    # Resolve strategy and tier
    if args.lite or args.industrial or args.strategy:
        strategy = args.strategy or "full"
        tier = "lite" if args.lite else ("industrial" if args.industrial else "standard")
    else:
        results = ask_user_install_strategy()
        if not results: return
        strategy = results['strategy']
        tier = results['tier']
    
    if strategy == 'manual':
        return
    
    central = get_mcp_tools_home()
    
    # 0. Universal Pre-flight
    if not pre_flight_checks(central):
        sys.exit(1)

    try:
        if strategy == 'full':
            install_to_central(central, workspace)
            
            if tier == 'industrial':
                setup_nexus_venv(central)
                create_hardened_entry_points(central)
                ensure_global_path(central)
            
            if tier != 'lite':
                generate_integrity_manifest(central)
                
            print(f"\n✅ Complete! Tools available at {central} [Tier: {tier.upper()}]")
            if tier == 'industrial':
                print("💡 Try running 'mcp-surgeon --help' in a new terminal.")
        elif strategy == 'step':
            if ask("Install to central location?"): 
                install_to_central(central, workspace)
                
                if tier == 'industrial':
                    if ask("Setup Nexus Venv and dependencies?"):
                        setup_nexus_venv(central)
                    if ask("Create hardened global entry points?"):
                        create_hardened_entry_points(central)
                    if ask("Integrate Nexus into your global PATH?"):
                        ensure_global_path(central)
                
                if tier != 'lite':
                    if ask("Generate Integrity Manifest?"):
                        generate_integrity_manifest(central)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        rollback()
        sys.exit(1)

    # Post-Install GUI Launch
    if args.gui:
        print("\n🚀 Launching GUI Dashboard...")
        try:
            if platform.system() == "Windows":
                 # Windows doesn't like execv overlay as much, subproc better
                subprocess.run([sys.executable, "-m", "mcp_inventory.cli", "gui"])
            else:
                # Try to launch via the start script if available for better context
                start_script = Path(__file__).parent / "start_gui.sh"
                if start_script.exists():
                     os.execl(str(start_script), str(start_script))
                else:
                     os.execl(sys.executable, sys.executable, "-m", "mcp_inventory.cli", "gui")
        except Exception as e:
            print(f"⚠️  Failed to launch GUI: {e}")

if __name__ == "__main__":
    main()
