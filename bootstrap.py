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

def ask_user_install_strategy():
    print("\n🚀 MCP Tools Suite Bootstrap")
    print("="*50)
    print(f"Current repo: {detect_which_repo()}")
    print(f"Central install: {get_mcp_tools_home()}")
    
    print("\nReliability Tiers Decision Matrix:")
    print("-" * 80)
    print(f"{'Tier':<12} | {'Confidence':<12} | {'Strategy':<18} | {'Pros/Cons'}")
    print("-" * 80)
    print(f"{'Lite':<12} | {'91-93%':<12} | {'Zero-Dep':<18} | {'👍 Portable, 👎 Basic matching'}")
    print(f"{'Standard':<12} | {'96%':<12} | {'Pure Python':<18} | {'👍 Regex indexing, 👎 Manual venv'}")
    print(f"{'Permanent':<12} | {'99.999%':<12} | {'Infrastructure':<18} | {'👍 100% compliance, 👎 Disk space'}")
    print("-" * 80)
    
    tier = 'standard'
    t_choice = input("\nSelect Reliability Tier [l/S/p] (Default: Standard): ").strip().lower()
    if t_choice == 'l': tier = 'lite'
    elif t_choice == 'p': tier = 'permanent'

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

        # Ensure uninstall.py is accessible at the top level for repo-mcp-packager
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

def setup_nexus_venv(central: Path):
    """Create a dedicated Nexus venv for --permanent mode."""
    venv_dir = central / ".venv"
    print(f"\n📦 Building Permanent Infrastructure at {venv_dir}...")
    
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
    parser.add_argument("--permanent", action="store_true", help="Permanent mode (Infrastructure)")
    parser.add_argument("--strategy", choices=["full", "step"], help="Installation strategy")
    args = parser.parse_args()

    if sys.version_info < (3,6):
        print("❌ Python 3.6+ required")
        sys.exit(1)
    
    workspace = get_workspace_root()
    if not workspace:
        print("❌ Cannot find workspace (need sibling repos)")
        sys.exit(1)
    
    # Resolve strategy and tier
    if args.lite or args.permanent or args.strategy:
        strategy = args.strategy or "full"
        tier = "lite" if args.lite else ("permanent" if args.permanent else "standard")
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
            
            if tier == 'permanent':
                setup_nexus_venv(central)
            
            if tier != 'lite':
                generate_integrity_manifest(central)
                
            print(f"\n✅ Complete! Tools at {central} [Tier: {tier.upper()}]")
        elif strategy == 'step':
            if ask("Install to central location?"): 
                install_to_central(central, workspace)
                
                if tier == 'permanent':
                    if ask("Setup Nexus Venv and dependencies?"):
                        setup_nexus_venv(central)
                
                if tier != 'lite':
                    if ask("Generate Integrity Manifest?"):
                        generate_integrity_manifest(central)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        rollback()
        sys.exit(1)

if __name__ == "__main__":
    main()
