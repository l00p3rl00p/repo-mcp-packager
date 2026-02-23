import os, sys, shutil, platform, argparse, hashlib, subprocess, json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, TypedDict, Any, Dict, List

from nexus_devlog import prune_devlogs, devlog_path, log_event, run_capture

# AGENT O: Integration
try:
    from nexus_session_logger import NexusSessionLogger
    SessionLogger = NexusSessionLogger()
except ImportError:
    SessionLogger = None

DEVLOG: Optional[Path] = None
FORCE_HEADLESS: bool = False

# Workforce Nexus Global Registry
GITHUB_ROOT = "https://github.com/l00p3rl00p"
NEXUS_REPOS = {
    'mcp-injector': f"{GITHUB_ROOT}/mcp-injector.git",
    'mcp-link-library': f"{GITHUB_ROOT}/mcp-link-library.git",
    'mcp-server-manager': f"{GITHUB_ROOT}/mcp-server-manager.git",
    'repo-mcp-packager': f"{GITHUB_ROOT}/repo-mcp-packager.git"
}

# Track artifacts for universal rollback
INSTALLED_ARTIFACTS = []

STATE_FILENAME = ".nexus_state.json"
SUITE_MANIFEST_PATH = Path(".nexus") / "manifest.json"

class _InstallState(TypedDict, total=False):
    installed: bool
    tier: str
    last_action: str
    last_updated_utc: str

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def get_install_state_path(central: Path) -> Path:
    return central / STATE_FILENAME

def load_install_state(central: Path) -> _InstallState:
    path = get_install_state_path(central)
    if not path.exists():
        return {"installed": False}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {"installed": True}
        out: _InstallState = {"installed": bool(raw.get("installed", True))}
        if isinstance(raw.get("tier"), str):
            out["tier"] = raw["tier"]
        if isinstance(raw.get("last_action"), str):
            out["last_action"] = raw["last_action"]
        if isinstance(raw.get("last_updated_utc"), str):
            out["last_updated_utc"] = raw["last_updated_utc"]
        return out
    except Exception:
        # Malformed state should never block installs; treat as "installed but unknown".
        return {"installed": True}

def save_install_state(central: Path, *, installed: bool, tier: Optional[str], last_action: str) -> None:
    path = get_install_state_path(central)
    try:
        payload: _InstallState = {
            "installed": bool(installed),
            "last_action": last_action,
            "last_updated_utc": _utc_now_iso(),
        }
        if tier:
            payload["tier"] = tier
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Failed to write install state: {e}")

def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def suite_manifest_path(central: Path) -> Path:
    return central / SUITE_MANIFEST_PATH

def _git_rev(repo_dir: Path) -> Optional[str]:
    try:
        if not (repo_dir / ".git").exists():
            return None
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()
    except Exception:
        return None

def write_suite_manifest(*, central: Path, tier: str, action: str, workspace: Optional[Path]) -> None:
    """
    Write a suite-level install manifest/receipt under the central install root (~/.mcp-tools).

    Design intent:
    - Every repo installs to the same place.
    - Logs/receipts should be centralized.
    - Uninstall/purge can be checklist-driven using owned surfaces.
    """
    try:
        manifest = {
            "type": "nexus-suite-manifest",
            "version": "1.0",
            "written_at_utc": _utc_now_iso(),
            "central_root": str(central),
            "tier": tier,
            "action": action,
            "workspace_source": str(workspace) if workspace else None,
            "repos": [],
            "owned_surfaces": [
                str(central),
                str(Path.home() / ".mcpinv"),
                str(Path.home() / "Desktop" / "Start Nexus.command"),
                str(Path.home() / "Desktop" / "Start Nexus.bat"),
            ],
            "logs_root": str(Path.home() / ".mcpinv"),
            "wrappers": {
                "central_bin": str(central / "bin"),
                "user_bin_default": str(_default_user_wrappers_dir() or ""),
            },
            "notes": [
                "This receipt is written by repo-mcp-packager/bootstrap.py.",
                "Per-repo packager manifests may exist under <project>/.librarian/manifest.json (standalone packaging).",
            ],
        }

        repos: List[Dict[str, Any]] = []
        for name in ("repo-mcp-packager", "mcp-injector", "mcp-server-manager", "mcp-link-library"):
            repo_dir = central / name
            repos.append(
                {
                    "name": name,
                    "path": str(repo_dir),
                    "present": repo_dir.exists(),
                    "git_rev": _git_rev(repo_dir),
                }
            )
        manifest["repos"] = repos

        _atomic_write_json(suite_manifest_path(central), manifest)
        print(f"✅ Suite manifest written to {suite_manifest_path(central)}")
    except Exception as e:
        print(f"⚠️  Failed to write suite manifest: {e}")

def detect_existing_install(central: Path) -> bool:
    """
    Detect whether the Nexus suite appears to be installed in central (~/.mcp-tools).
    Keep this lightweight; it should not ever throw.
    """
    try:
        if not central.exists():
            return False
        markers = [
            central / "repo-mcp-packager",
            central / "mcp-injector",
            central / "mcp-server-manager",
            central / "mcp-link-library",
            central / "bin" / "mcp-activator",
        ]
        return any(p.exists() for p in markers)
    except Exception:
        return True

def git_available():
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def _is_probably_git_url(value: str) -> bool:
    v = value.strip()
    if not v:
        return False
    if v.startswith(("https://", "http://")):
        return True
    # SSH style: git@github.com:org/repo.git
    if v.startswith("git@") and ":" in v:
        return True
    return False

def fetch_nexus_repo(name: str, target_dir: Path, update=False, url_override: Optional[str] = None):
    """Fetch a repo from GitHub if missing, or update if requested."""
    url = url_override or NEXUS_REPOS.get(name)
    if not url:
        return False
    if url_override and not _is_probably_git_url(url_override):
        print(f"❌ Invalid repo URL for {name}. Expected https://... or git@...:...")
        return False
    
    if not git_available():
        print(f"❌ Git not found. Cannot manage {name} automatically.")
        return False
        
    try:
        if target_dir.exists() and (target_dir / ".git").exists():
            if update:
                print(f"🔄 Updating {name}...")
                # Harden: if in industrial/managed mode, we should be able to force a clean update
                # to avoid the 'local changes' error seen in logs.
                try:
                    # Attempt a clean pull: reset any manual patches or untracked logs
                    subprocess.run(["git", "-C", str(target_dir), "reset", "--hard", "HEAD"], check=False)
                    subprocess.run(["git", "-C", str(target_dir), "clean", "-fd"], check=False)
                    
                    if DEVLOG:
                        run_capture(["git", "-C", str(target_dir), "pull"], devlog=DEVLOG, check=True)
                    else:
                        subprocess.run(["git", "-C", str(target_dir), "pull"], check=True)
                    return True
                except subprocess.CalledProcessError:
                    # If pull fails (e.g. network), we still return True if the dir exists, 
                    # but we warn the user.
                    print(f"⚠️  Failed to pull latest for {name}. Using cached version.")
                    return True
            return True
            
        print(f"📥 Fetching {name} from GitHub...")
        if target_dir.exists():
            shutil.rmtree(target_dir)
            
        if DEVLOG:
            run_capture(["git", "clone", "--depth", "1", url, str(target_dir)], devlog=DEVLOG, check=True)
        else:
            subprocess.run(["git", "clone", "--depth", "1", url, str(target_dir)], check=True)
        return True
    except Exception as e:
        print(f"❌ Failed to fetch/update {name}: {e}")
        log_event(DEVLOG, "fetch_repo_failed", {"repo": name, "target": str(target_dir), "error": str(e)})
        return False

def get_mcp_tools_home():
    if platform.system() == "Windows":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"

def _is_running_in_venv() -> bool:
    if os.environ.get("VIRTUAL_ENV"):
        return True
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    return sys.prefix != base_prefix

def _preferred_system_python3() -> Optional[Path]:
    """
    Select a stable, non-virtualenv python3 for bootstrapping Nexus infrastructure.

    Why: if bootstrap.py is run from inside some project venv, using sys.executable to seed
    ~/.mcp-tools/.venv can cause the new venv's interpreter to point at that project venv,
    effectively "taking over" global wrappers.
    """
    candidates: list[Path] = []

    # macOS has a stable baseline python3 location (CommandLineTools).
    if platform.system() != "Windows":
        candidates.append(Path("/usr/bin/python3"))

    for name in ("python3", "python"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))

    active_venv = os.environ.get("VIRTUAL_ENV")
    for candidate in candidates:
        try:
            if not candidate.exists() or not os.access(candidate, os.X_OK):
                continue
            resolved = candidate.resolve()
            if active_venv and str(resolved).startswith(active_venv.rstrip("/") + "/"):
                continue
            return resolved
        except Exception:
            continue
    return None

def _nexus_python(central: Path) -> Path:
    """
    Prefer the Nexus-managed venv python when present; otherwise fall back to a system python3.
    """
    if platform.system() == "Windows":
        venv_python = central / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = central / ".venv" / "bin" / "python"
    if venv_python.exists() and os.access(venv_python, os.X_OK):
        return venv_python
    return _preferred_system_python3() or Path(sys.executable)

def _default_user_wrappers_dir() -> Optional[Path]:
    if platform.system() == "Windows":
        return None
    return Path.home() / ".local" / "bin"

def install_user_wrappers(
    *,
    central: Path,
    wrappers_dir: Path,
    overwrite: bool = False,
    verbose: bool = False,
) -> None:
    """
    Install short-command wrappers into a common user bin directory (default: ~/.local/bin).

    This avoids editing shell RC files by default while still giving users short, global-ish commands.
    """
    marker = "# Workforce Nexus User Wrapper (managed by repo-mcp-packager)"
    wrappers_dir.mkdir(parents=True, exist_ok=True)

    commands = {
        "mcp-surgeon": central / "bin" / "mcp-surgeon",
        "mcp-observer": central / "bin" / "mcp-observer",
        "mcp-librarian": central / "bin" / "mcp-librarian",
        "mcp-activator": central / "bin" / "mcp-activator",
        # Rule of Ones: one front door.
        "nexus": central / "bin" / "nexus",
    }

    for name, target in commands.items():
        if not target.exists():
            continue

        dest = wrappers_dir / name
        if dest.exists() and not overwrite:
            # Only skip if it's not ours. If it's ours, we can refresh it.
            try:
                if dest.is_file() and marker in dest.read_text(encoding="utf-8", errors="ignore"):
                    pass
                else:
                    if verbose:
                        print(f"ℹ️  Wrapper exists; skipping: {dest}")
                    continue
            except Exception:
                if verbose:
                    print(f"ℹ️  Wrapper exists; skipping: {dest}")
                continue

        script = f"""#!/usr/bin/env bash
set -euo pipefail
{marker}
exec "{target}" "$@"
"""
        try:
            dest.write_text(script, encoding="utf-8")
            dest.chmod(dest.stat().st_mode | 0o111)
            if verbose:
                print(f"✅ Installed user wrapper: {dest}")
        except Exception as e:
            print(f"⚠️  Failed to install wrapper {dest}: {e}")

def _is_central_install_dir(path: Path) -> bool:
    try:
        central = get_mcp_tools_home().resolve()
        candidate = path.resolve()
        if candidate == central:
            return True
        return candidate.samefile(central)
    except Exception:
        return False

def get_workspace_root():
    """
    Find the workspace root without walking up directories.
    Policy: never scan the disk / walk up directory trees. We only check:
    - the current working directory (cwd)
    - the parent of this script's directory (sibling workspace)
    """
    siblings = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']

    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
        # NEW: Check if this script itself is inside a sibling repo and look at its PARENT
        Path(__file__).resolve().parent.parent.parent
    ]
    for base in candidates:
        try:
            if not base or not base.is_dir():
                continue
            # Never treat the central install dir (~/.mcp-tools) as a source workspace.
            if _is_central_install_dir(base):
                continue
            found = [s for s in siblings if (base / s).is_dir()]
            if len(found) >= 2:
                return base
        except Exception:
            continue
    return None

def _load_central_config(central: Path) -> dict:
    """
    Best-effort load of ~/.mcp-tools/config.json.
    Must never throw; config is optional.
    """
    try:
        cfg_path = central / "config.json"
        if not cfg_path.exists():
            return {}
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}

def _get_extra_repos_from_config(config: dict) -> dict:
    """
    Optional extension point for installing additional repos alongside the Nexus suite.

    Expected format:
      "extra_repos": { "my-repo": "git@github.com:org/my-repo.git" }
    """
    extra = config.get("extra_repos")
    if not isinstance(extra, dict):
        return {}
    out: dict = {}
    for name, url in extra.items():
        if isinstance(name, str) and isinstance(url, str) and name.strip() and url.strip():
            out[name.strip()] = url.strip()
    return out

def detect_which_repo():
    return Path(__file__).parent.name

def detect_full_suite(workspace: Path):
    """Check if we are in a Workforce Nexus workspace (all 4 repos)."""
    if not workspace: return False
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
    if FORCE_HEADLESS:
        print(f"[*] (Headless) Automatically accepted: {question}")
        return True
    print(f"\n❓ {question}")
    while True:
        r = input("   [Y/n]: ").strip().lower()
        if r in ['y','yes','']: return True
        if r in ['n','no']: return False

def ask_choice(prompt: str, choices: dict, default: Optional[str] = None) -> str:
    """
    Prompt user to choose a key from choices (TTY only). Returns the chosen key.
    choices: key -> description
    """
    print(f"\n{prompt}")
    for key, desc in choices.items():
        print(f"  [{key}] {desc}")
    d = f" (Default: {default})" if default else ""
    while True:
        r = input(f"\nChoice{d}: ").strip().lower()
        if not r and default:
            return default
        if r in choices:
            return r

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

def install_to_central(central, workspace=None, update=False):
    """Deploy repos to central location (~/.mcp-tools). Fetches from Git if workspace is missing."""
    central.mkdir(parents=True, exist_ok=True)
    
    # Define our components
    repos = ['mcp-injector', 'repo-mcp-packager', 'mcp-server-manager', 'mcp-link-library']
    config = _load_central_config(central)
    extra_repos = _get_extra_repos_from_config(config)
    if extra_repos:
        for extra_name in extra_repos.keys():
            if extra_name not in repos:
                repos.append(extra_name)

    # Workspace environment conflict warning (no disk scanning; only direct checks)
    if workspace:
        env_file = workspace / ".env"
        if env_file.exists():
            print("📝 Note: Found a workspace `.env` file.")
            print("   This can cause unintended conflicts with the central install in ~/.mcp-tools.")
            print(f"   Path: {env_file}")
    
    for repo in repos:
        source = workspace / repo if (workspace and (workspace / repo).exists()) else None
        target = central / repo
        
        if source:
            env_file = source / ".env"
            if env_file.exists():
                print(f"📝 Note: Found `.env` inside {repo}.")
                print("   A workspace `.env` can cause unintended conflicts with the central install in ~/.mcp-tools.")
                print(f"   Path: {env_file}")
            # Mode A: Active Workspace Copy (Developer Mode)
            if target.exists():
                try:
                    shutil.rmtree(target)
                except Exception as e:
                    print(f"❌ Failed to remove existing {repo}: {e}")
                    raise e
            
            try:
                # We copy the source. If it has .git, we copy it too (optional, but requested for 'can be updated')
                shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '.venv', 'node_modules', '.DS_Store'))
                INSTALLED_ARTIFACTS.append(target)
                ensure_executable(target)
                print(f"✅ Installed {repo} (Local Source)")
            except Exception as e:
                print(f"❌ Failed to copy {repo}: {e}")
                raise e
        else:
            # Mode B: GitHub Discovery (Autonomous/Standalone Mode)
            url_override = extra_repos.get(repo) if extra_repos else None
            if fetch_nexus_repo(repo, target, update=update, url_override=url_override):
                if target not in INSTALLED_ARTIFACTS:
                    INSTALLED_ARTIFACTS.append(target)
                ensure_executable(target)
            else:
                print(f"⚠️  Skipping {repo}: Source not found and fetch failed.")

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

def install_converged_application(
    tier,
    workspace,
    update: bool = False,
    add_to_path: bool = False,
    user_wrappers: bool = True,
    wrappers_dir: Optional[Path] = None,
    overwrite_wrappers: bool = False,
    verbose: bool = False,
):
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
        ensure_suite_index_prereqs(central)
        prompt_for_client_injection(workspace=workspace, central=central, tier=tier)
            
    elif tier == 'industrial':
        # Industrial: Managed Mirror (Copy/Git)
        # We reuse install_to_central logic but ensure global venv
        install_to_central(central, workspace, update=update)
        setup_nexus_venv(central)
        create_hardened_entry_points(central)
        if add_to_path:
            ensure_global_path(central)
        if user_wrappers and (wrappers_dir or _default_user_wrappers_dir()):
            install_user_wrappers(
                central=central,
                wrappers_dir=wrappers_dir or _default_user_wrappers_dir(),  # type: ignore[arg-type]
                overwrite=overwrite_wrappers,
                verbose=verbose,
            )
        ensure_suite_index_prereqs(central)
        prompt_for_client_injection(workspace=workspace, central=central, tier=tier)
        # Trigger Librarian Synergy (Lazy sync)
        print("🧠 Triggering Librarian Suite Indexing...")
        try:
            cmd = [str(_nexus_python(central)), str(central / "mcp-link-library" / "mcp.py"), "--index-suite"]
            if DEVLOG:
                run_capture(cmd, devlog=DEVLOG, check=False)
            else:
                subprocess.run(cmd, check=False)
        except Exception as e:
            print(f"⚠️  Indexing minor issue: {e} (Installation still successful)")
            log_event(DEVLOG, "suite_index_failed", {"error": str(e)})

    print("\n" + "="*60)
    print(f"✅  INSTALLATION SUCCESSFUL (Tier: {tier.upper()})")
    print("="*60)
    print(f"Your Nexus environment is fully configured.")
    print(f"Tools available in: {central}/bin")
    print("-" * 60)
    print(f"📊 GUI Dashboard Access:")
    print(f"   Command: mcp-observer gui")
    print(f"   URL:     http://localhost:8501")
    print("-" * 60)
    if add_to_path:
        print(f"Log out and back in to refresh your path, or run:")
        print(f"  source ~/.zshrc  (or ~/.bashrc)")
    else:
        print("ℹ️  Shell PATH was NOT modified (default).")
        print(f"   Run directly: {central}/bin/mcp-activator (etc.)")
        print("   Or re-run with --add-to-path to add ~/.mcp-tools/bin to your shell PATH.")
    if user_wrappers and (wrappers_dir or _default_user_wrappers_dir()):
        print("-" * 60)
        print(f"✅ User wrappers installed to: {wrappers_dir or _default_user_wrappers_dir()}")
        print("   If that directory is not on your PATH, add it manually (recommended):")
        print('     export PATH="$HOME/.local/bin:$PATH"')
    print("="*60 + "\n")

def setup_nexus_venv(central: Path):
    """Create a dedicated Nexus venv for --industrial mode."""
    venv_dir = central / ".venv"
    print(f"\n📦 Building Industrial Infrastructure at {venv_dir}...")
    
    try:
        base_python = _preferred_system_python3() or Path(sys.executable)
        if _is_running_in_venv():
            print(f"ℹ️  Detected active virtualenv; seeding Nexus venv with: {base_python}")
        if DEVLOG:
            run_capture([str(base_python), "-m", "venv", str(venv_dir)], devlog=DEVLOG, check=True)
        else:
            subprocess.run([str(base_python), "-m", "venv", str(venv_dir)], check=True)
        
        # Determine pip path
        if platform.system() == "Windows":
            pip = venv_dir / "Scripts" / "pip.exe"
        else:
            pip = venv_dir / "bin" / "pip"
            
        # 1. Upgrade pip to silence warnings and ensure compatibility
        print("⬆️  Upgrading pip to latest version...")
        try:
            if DEVLOG:
                run_capture([str(pip), "install", "--upgrade", "pip"], devlog=DEVLOG, check=True)
            else:
                subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️  Pip upgrade failed, attempting to continue with current version...")

        print("📥 Installing high-confidence libraries (pathspec, jsonschema, psutil, PyYAML)...")
        # 2. Allow interactive prompts if packages need them
        if DEVLOG:
            run_capture([str(pip), "install", "pathspec", "jsonschema", "psutil", "PyYAML"], devlog=DEVLOG, check=True)
        else:
            subprocess.run([str(pip), "install", "pathspec", "jsonschema", "psutil", "PyYAML"], check=True)
        
        print("✅ Nexus Venv ready.")
        return True
    except Exception as e:
        print(f"❌ Failed to setup Nexus Venv: {e}")
        log_event(DEVLOG, "venv_setup_failed", {"error": str(e), "venv_dir": str(venv_dir)})
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
    
    # Note: We still embed the venv python path, but wrappers are runtime-robust:
    # if the venv python is missing (e.g., user deleted ~/.mcp-tools/.venv), wrappers fall back to system python.
    venv_python_str = str(venv_python)

    # Command mapping: entry_name -> (repo_dir, module_path, use_python_m)
    commands = {
        "mcp-surgeon": ("mcp-injector", "mcp_injector.py", False),
        "mcp-observer": ("mcp-server-manager", "mcp_inventory/cli.py", True), # Uses -m mcp_inventory.cli
        "mcp-librarian": ("mcp-link-library", "mcp.py", False),
        "mcp-activator": ("repo-mcp-packager", "bootstrap.py", False),
        # Nexus Control Surface (local GUI command runner). Kept as a separate entry point
        # so it remains usable from the central install even if the original workspace is deleted.
        "mcp-nexus-gui": ("repo-mcp-packager", "gui/server.py", False),
        # Rule of Ones: single front-door launcher.
        # `nexus` with no flags should open the guided CLI walkthrough (anti-lazy menu),
        # not launch a specific subsystem or print help.
        # Power users can still pass flags (e.g. --sync, --gui) and the bootstrapper will route them.
        "nexus": ("repo-mcp-packager", "bootstrap.py", False),
    }
    
    for cmd, (repo, module, use_m) in commands.items():
        cmd_path = bin_dir / cmd
        target_script = central / repo / module
        
        if not target_script.exists():
            continue
            
        # Write the hardened wrapper
        # We add 'central' to PYTHONPATH so modules like mcp_inventory can be found
        if use_m:
            # For mcp-observer, we want `python -m mcp_inventory.cli`
            module_name = module.replace("/", ".").replace(".py", "")
            wrapper = f"""#!/bin/bash
# Workforce Nexus Hardened Wrapper
VENV_PY="{venv_python_str}"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  if [[ -x "/usr/bin/python3" ]]; then
    PY="/usr/bin/python3"
  else
    PY="$(command -v python3 || command -v python)"
  fi
fi
export PYTHONPATH="{central}/mcp-server-manager:$PYTHONPATH"
"$PY" -m {module_name} "$@"
"""
        else:
            wrapper = f"""#!/bin/bash
# Workforce Nexus Hardened Wrapper
VENV_PY="{venv_python_str}"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  if [[ -x "/usr/bin/python3" ]]; then
    PY="/usr/bin/python3"
  else
    PY="$(command -v python3 || command -v python)"
  fi
fi
export PYTHONPATH="{central}/mcp-injector:{central}/mcp-link-library:{central}/mcp-server-manager:{central}/repo-mcp-packager:$PYTHONPATH"
"$PY" "{target_script}" "$@"
"""
        try:
            cmd_path.write_text(wrapper)
            cmd_path.chmod(cmd_path.stat().st_mode | 0o111)
            print(f"✅ Created hardened entry point: {cmd}")
        except Exception as e:
            print(f"❌ Failed to create entry point {cmd}: {e}")


def ensure_suite_index_prereqs(central: Path) -> None:
    """
    Ensure Librarian suite indexing has stable inputs immediately after install.
    - Observer inventory: ~/.mcp-tools/mcp-server-manager/inventory.yaml
    - Injector global config: ~/.mcp-tools/config.json
    """
    try:
        inv_path = central / "mcp-server-manager" / "inventory.yaml"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        if not inv_path.exists():
            inv_path.write_text("servers: []\n", encoding="utf-8")

        cfg_path = central / "config.json"
        if not cfg_path.exists():
            cfg_path.write_text(json.dumps({"ide_config_paths": {}}, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Suite indexing prereqs not created: {e}")

def run_uninstaller(central: Path) -> int:
    """
    Best-effort uninstaller. Prefer the packaged uninstall.py if present.
    Returns process exit code (0 == success).
    """
    uninstaller = central / "repo-mcp-packager" / "uninstall.py"
    if not uninstaller.exists():
        uninstaller = central / "repo-mcp-packager" / "serverinstaller" / "uninstall.py"
    if not uninstaller.exists():
        print("❌ Uninstaller not found in central install.")
        print(f"   Expected: {central}/repo-mcp-packager/uninstall.py")
        return 2
    try:
        cmd = [str(_nexus_python(central)), str(uninstaller), "--kill-venv", "--purge-data"]
        return subprocess.call(cmd)
    except Exception as e:
        print(f"❌ Failed to run uninstaller: {e}")
        return 2

def run_injector_config_flow(workspace: Optional[Path], central: Path, tier: Optional[str]) -> int:
    """
    Best-effort "anti-lazy" injector setup:
    - Prefer --startup-detect (guided, auto-detects IDEs)
    - Otherwise list clients and allow one-shot --add
    """
    try:
        if tier == "industrial":
            injector = central / "mcp-injector" / "mcp_injector.py"
        elif workspace:
            injector = workspace / "mcp-injector" / "mcp_injector.py"
        else:
            injector = central / "mcp-injector" / "mcp_injector.py"

        if not injector.exists():
            print("❌ Injector not found; cannot configure clients.")
            return 2

        # Guided flow (recommended)
        try:
            return subprocess.call([str(_nexus_python(central)), str(injector), "--startup-detect"])
        except Exception:
            pass

        # Fallback flow
        print("\n🧩 Injector Quickstart")
        print("-" * 60)
        subprocess.call([str(_nexus_python(central)), str(injector), "--list-clients"])
        client = input("\nType the client name to add (e.g., claude): ").strip()
        if not client:
            print("⚠️  No client selected; skipping injector config.")
            return 0
        return subprocess.call([str(_nexus_python(central)), str(injector), "--client", client, "--add"])
    except Exception as e:
        print(f"❌ Injector config flow failed: {e}")
        return 2

def launch_gui(central: Path) -> int:
    observer_bin = central / "bin" / "mcp-observer"
    try:
        if observer_bin.exists():
            return subprocess.call([str(observer_bin), "gui"])

        venv_python = central / ".venv" / "bin" / "python"
        if platform.system() == "Windows":
            venv_python = central / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = sys.executable

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{central}/mcp-server-manager:{env.get('PYTHONPATH', '')}"
        return subprocess.call([str(venv_python), "-m", "mcp_inventory.cli", "gui"], env=env)
    except Exception as e:
        print(f"⚠️  Failed to launch GUI: {e}")
        print("   Try running it manually: mcp-observer gui")
        return 2

def rerun_action_menu(*, workspace: Optional[Path], central: Path, last_tier: Optional[str]) -> str:
    """
    Interactive menu shown on re-runs so users can easily find uninstall/config/gui
    without hunting docs.
    """
    if not sys.stdin.isatty():
        return "continue"

    print("\n♻️  Nexus Installer Re-run Detected")
    print("=" * 60)
    print(f"Central install: {central}")
    if last_tier:
        print(f"Last tier:      {last_tier}")
    print("-" * 60)
    print("Pick what you want to do now (anti-lazy mode).")

    choice = ask_choice(
        "Actions:",
        {
            "1": "Install / Repair (recommended)",
            "2": "Configure IDE injection (create/update global config)",
            "3": "Launch GUI (Observer dashboard)",
            "4": "Uninstall (wipe: venv + data)",
            "5": "Exit",
        },
        default="1",
    )

    if choice == "2":
        run_injector_config_flow(workspace, central, last_tier)
        return "exit"
    if choice == "3":
        launch_gui(central)
        return "exit"
    if choice == "4":
        rc = run_uninstaller(central)
        save_install_state(central, installed=(rc != 0), tier=last_tier, last_action="uninstall")
        return "exit"
    if choice == "5":
        return "exit"
    return "continue"


def prompt_for_client_injection(workspace: Path, central: Path, tier: str) -> None:
    """
    Ask which IDE clients to inject during install (TTY only).
    Uses mcp-injector's startup-detect flow to keep logic centralized.
    """
    try:
        if FORCE_HEADLESS or not sys.stdin.isatty():
            return
        print("\nIDE injection (optional)")
        print("- This step is opt-in (no automatic injection).")
        print("- You can safely skip by answering 'N' in the next prompt.")

        if tier == "industrial":
            injector = central / "mcp-injector" / "mcp_injector.py"
        else:
            injector = workspace / "mcp-injector" / "mcp_injector.py"

        if not injector.exists():
            print("Warning: injector not found; skipping IDE injection prompt.")
            return

        if DEVLOG:
            run_capture([sys.executable, str(injector), "--startup-detect"], devlog=DEVLOG, check=False)
        else:
            subprocess.run([sys.executable, str(injector), "--startup-detect"], check=False)
    except Exception as e:
        print(f"Warning: IDE injection prompt skipped: {e}")
        log_event(DEVLOG, "ide_injection_prompt_failed", {"error": str(e)})

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
    parser = argparse.ArgumentParser(
        description="Nexus Bootstrap - Tiered Reliability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands (what they do):\n"
            "  mcp-activator --sync             Update the central install (workspace or GitHub)\n"
            "  mcp-activator --permanent        Install/repair the full suite into ~/.mcp-tools\n"
            "  mcp-activator --gui              Launch GUI after install/sync\n"
            "\n"
            "Common flows:\n"
            "  Install:   python3 bootstrap.py --permanent\n"
            "  Update:    python3 bootstrap.py --sync\n"
            "  GUI:       python3 bootstrap.py --permanent --gui\n"
        ),
    )
    parser.add_argument("--lite", action="store_true", help="Lite mode (Zero-Dep)")
    parser.add_argument("--industrial", "--permanent", action="store_true", dest="industrial", help="Industrial mode (Infrastructure)")
    parser.add_argument("--sync", "--update", action="store_true", dest="sync", help="Sync/Update Workforce Nexus from workspace or GitHub")
    parser.add_argument("--workspace", type=str, help="Explicit source workspace root (must contain Nexus repos as siblings)")
    parser.add_argument("--strategy", choices=["full", "step"], help="Installation strategy")
    parser.add_argument("--gui", action="store_true", help="Launch GUI after installation")
    parser.add_argument("--add-to-path", action="store_true", help="Opt-in: add ~/.mcp-tools/bin to shell PATH (edits ~/.zshrc or ~/.bashrc)")
    parser.add_argument("--no-user-wrappers", action="store_true", help="Do not install short-command wrappers into a user bin dir (default: ~/.local/bin)")
    parser.add_argument("--wrappers-dir", type=str, help="Directory to install user wrappers into (default: ~/.local/bin)")
    parser.add_argument("--overwrite-wrappers", action="store_true", help="Overwrite existing user wrappers if present")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing installations")
    parser.add_argument("--repair", action="store_true", help="Repair venv and entry points without full re-install")
    parser.add_argument("--headless", action="store_true", help="Run without interactive prompts (Agent Mode)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output + devlog-friendly prints")
    parser.add_argument("--devlog", action="store_true", help="Write dev log (JSONL) with 90-day retention")
    args = parser.parse_args()
    
    if args.headless:
        global FORCE_HEADLESS
        FORCE_HEADLESS = True

    if args.devlog:
        prune_devlogs(days=90)
        global DEVLOG
        DEVLOG = devlog_path()
        log_event(DEVLOG, "bootstrap_start", {"argv": sys.argv})
        if args.verbose:
            print(f"[-] Devlog: {DEVLOG}")
            
    if SessionLogger:
        SessionLogger.log("INFO", "Nexus Bootstrap Initiated", suggestion="Checking workspace integrity...")

    if args.sync:
        workspace = None
        if args.workspace:
            candidate = Path(args.workspace).expanduser()
            if candidate.exists() and candidate.is_dir() and not _is_central_install_dir(candidate):
                workspace = candidate
            else:
                print(f"⚠️  Ignoring invalid --workspace: {args.workspace}")
        if not workspace:
            workspace = get_workspace_root()

        # Only a full dev workspace should be used as the *source* for sync.
        # If we can't prove that, fall back to GitHub update mode.
        if workspace and not detect_full_suite(workspace):
            print(f"🔄 Workspace incomplete at {workspace}; syncing Industrial Nexus via GitHub instead.")
            workspace = None

        if not workspace:
            print("🔄 No workspace found. Syncing Industrial Nexus via GitHub...")
            install_converged_application(
                'industrial',
                None,
                update=True,
                add_to_path=False,
                user_wrappers=not args.no_user_wrappers,
                wrappers_dir=Path(args.wrappers_dir).expanduser() if args.wrappers_dir else None,
                overwrite_wrappers=args.overwrite_wrappers,
                verbose=args.verbose,
            )
            log_event(DEVLOG, "bootstrap_end", {"rc": 0})
            return
        print(f"🔄 Syncing Industrial Nexus from local workspace: {workspace}")
        install_converged_application(
            'industrial',
            workspace,
            update=True,
            add_to_path=False,
            user_wrappers=not args.no_user_wrappers,
            wrappers_dir=Path(args.wrappers_dir).expanduser() if args.wrappers_dir else None,
            overwrite_wrappers=args.overwrite_wrappers,
            verbose=args.verbose,
        )
        log_event(DEVLOG, "bootstrap_end", {"rc": 0})
        return

    if args.repair:
        central = get_mcp_tools_home()
        print(f"🔧 Repairing Industrial Nexus Infrastructure at {central}...")
        
        # 0. Pre-flight
        if not pre_flight_checks(central):
            sys.exit(1)
            
        try:
            # Refresh venv
            setup_nexus_venv(central)
            
            # Refresh entry points
            create_hardened_entry_points(central)
            
            # Refresh user wrappers
            wrappers_dir = Path(args.wrappers_dir).expanduser() if args.wrappers_dir else _default_user_wrappers_dir()
            if wrappers_dir:
                install_user_wrappers(
                    central=central,
                    wrappers_dir=wrappers_dir,
                    overwrite=True,
                    verbose=args.verbose
                )
            
            # Refresh suite prereqs
            ensure_suite_index_prereqs(central)
            
            print("\n✅ Repair Completed. All entry points and venv refreshed.")
            save_install_state(central, installed=True, tier="industrial", last_action="repair")
            write_suite_manifest(central=central, tier="industrial", action="repair", workspace=get_workspace_root())
        except Exception as e:
            print(f"❌ Repair failed: {e}")
            sys.exit(1)
            
        log_event(DEVLOG, "bootstrap_end", {"rc": 0})
        return

    if sys.version_info < (3,6):
        print("❌ Python 3.6+ required")
        sys.exit(1)
    
    workspace = get_workspace_root()
    
    # Check if we are being run from within a potential target project
    target_project = Path(__file__).resolve().parent.parent
    has_project_files = any((target_project / f).exists() for f in ['package.json', 'pyproject.toml', 'requirements.txt', 'setup.py'])
    
    if not workspace:
        # Case A: Standalone Mode (Copied into another repo)
        if has_project_files and target_project.name not in ['mcp-injector', 'mcp-server-manager', 'mcp-link-library', 'repo-mcp-packager']:
            print(f"🎯 Target Project Detected: {target_project.name}")
            print(f"[*] This looks like a standalone setup for {target_project.name}.")
            
            installer = Path(__file__).parent / "serverinstaller" / "install.py"
            if installer.exists():
                print(f"🚀 Launching Standalone Installer...")
                os.execv(sys.executable, [sys.executable, str(installer)] + sys.argv[1:])
        
        # Case B: Autonomous Mode (Suite Install from GitHub)
        print("[*] No local Nexus workspace found. Entering Autonomous Mode...")
        if not args.industrial and not args.lite and not args.strategy:
             print("⚠️  No deployment tier selected. To install the Workforce Nexus suite from GitHub, use:")
             print("   python bootstrap.py --permanent")
             sys.exit(1)
    elif has_project_files and target_project.name not in ['mcp-injector', 'mcp-server-manager', 'mcp-link-library', 'repo-mcp-packager']:
        # Case C: Developer Workspace + Standalone Target
        print(f"🎯 Target Project Detected: {target_project.name}")
        installer = Path(__file__).parent / "serverinstaller" / "install.py"
        if installer.exists():
            os.execv(sys.executable, [sys.executable, str(installer)] + sys.argv[1:])
        
    # Phase 12: Convergence Check
    if detect_full_suite(workspace):
        if not args.lite and not args.industrial:
            # If no manual flags, prompt for convergence
            tier = ask_convergence_tier()
            install_converged_application(
                tier,
                workspace,
                add_to_path=args.add_to_path,
                user_wrappers=not args.no_user_wrappers,
                wrappers_dir=Path(args.wrappers_dir).expanduser() if args.wrappers_dir else None,
                overwrite_wrappers=args.overwrite_wrappers,
                verbose=args.verbose,
            )
            return
    else:
        # Partial or Autonomous Mode
        if workspace:
            print(f"⚠️  Partial workspace detected at {workspace}")
            print("   Proceeding with standard installation for available repos.")
            
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
    wrappers_dir = Path(args.wrappers_dir).expanduser() if args.wrappers_dir else None

    # Intelligent re-run behavior: when already installed, offer actions first.
    existing = detect_existing_install(central)
    state = load_install_state(central)
    if existing and not args.force and not args.sync:
        action = rerun_action_menu(workspace=workspace, central=central, last_tier=state.get("tier"))
        if action == "exit":
            return
    
    # 0. Universal Pre-flight
    if not pre_flight_checks(central):
        sys.exit(1)

    try:
        if strategy == 'full':
            install_to_central(central, workspace, update=args.force)
            
            if tier == 'industrial':
                setup_nexus_venv(central)
                create_hardened_entry_points(central)
                if args.add_to_path:
                    ensure_global_path(central)
                else:
                    print("ℹ️  Skipping shell PATH modification (use --add-to-path to opt in).")
                if not args.no_user_wrappers and (wrappers_dir or _default_user_wrappers_dir()):
                    install_user_wrappers(
                        central=central,
                        wrappers_dir=wrappers_dir or _default_user_wrappers_dir(),  # type: ignore[arg-type]
                        overwrite=args.overwrite_wrappers,
                        verbose=args.verbose,
                    )

            # Always make indexing/injection prerequisites available post-install.
            if tier != "lite":
                ensure_suite_index_prereqs(central)
                prompt_for_client_injection(
                    workspace=workspace or get_workspace_root() or (central / "suite"),
                    central=central,
                    tier=tier,
                )
            
            if tier != 'lite':
                generate_integrity_manifest(central)
                
            print(f"\n✅ Complete! Tools available at {central} [Tier: {tier.upper()}]")
            if tier == 'industrial':
                print("💡 Try running 'mcp-surgeon --help' in a new terminal.")
            save_install_state(central, installed=True, tier=tier, last_action="install_full")
            write_suite_manifest(central=central, tier=tier, action="install_full", workspace=workspace)
        elif strategy == 'step':
            if ask("Install to central location?"): 
                install_to_central(central, workspace, update=args.force)
                
                if tier == 'industrial':
                    if ask("Setup Nexus Venv and dependencies?"):
                        setup_nexus_venv(central)
                    if ask("Create hardened global entry points?"):
                        create_hardened_entry_points(central)
                    if not args.no_user_wrappers and (wrappers_dir or _default_user_wrappers_dir()) and ask("Install user wrappers to ~/.local/bin?"):
                        install_user_wrappers(
                            central=central,
                            wrappers_dir=wrappers_dir or _default_user_wrappers_dir(),  # type: ignore[arg-type]
                            overwrite=args.overwrite_wrappers,
                            verbose=args.verbose,
                        )
                    if ask("Integrate Nexus into your global PATH?"):
                        ensure_global_path(central)

                if tier != "lite":
                    if ask("Create suite prereqs (inventory + injector config)?"):
                        ensure_suite_index_prereqs(central)
                    if ask("Detect IDE clients and offer injection now?"):
                        prompt_for_client_injection(
                            workspace=workspace or get_workspace_root() or (central / "suite"),
                            central=central,
                            tier=tier,
                        )
                
                if tier != 'lite':
                    if ask("Generate Integrity Manifest?"):
                        generate_integrity_manifest(central)
            save_install_state(central, installed=True, tier=tier, last_action="install_step")
            write_suite_manifest(central=central, tier=tier, action="install_step", workspace=workspace)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        rollback()
        save_install_state(central, installed=False, tier=tier, last_action="install_failed")
        sys.exit(1)

    # Post-Install GUI Launch
    if args.gui:
        print("\n🚀 Launching GUI Dashboard...")
        # Use the hardened entry point if it exists, otherwise fall back to manual logic
        observer_bin = central / "bin" / "mcp-observer"
        
        try:
            if observer_bin.exists():
                os.execl(str(observer_bin), str(observer_bin), "gui")
            else:
                # Manual fallback with explicit PYTHONPATH
                venv_python = central / ".venv" / "bin" / "python"
                if platform.system() == "Windows":
                    venv_python = central / ".venv" / "Scripts" / "python.exe"
                
                if not venv_python.exists():
                    venv_python = sys.executable
                
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{central}/mcp-server-manager:{env.get('PYTHONPATH', '')}"
                
                cmd = [str(venv_python), "-m", "mcp_inventory.cli", "gui"]
                subprocess.run(cmd, env=env)
        except Exception as e:
            print(f"⚠️  Failed to launch GUI: {e}")
            print("   Try running it manually: mcp-observer gui")

if __name__ == "__main__":
    main()
