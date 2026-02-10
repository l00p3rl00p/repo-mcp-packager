import os
import sys
import subprocess
import shutil
import platform
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

@dataclass
class AuditResult:
    timestamp: str
    shell: str
    python_version: str
    in_venv: bool
    path_entries: List[str]
    node_present: bool
    npm_present: bool
    docker_present: bool
    docker_running: bool
    platforms: str
    env_vars: Dict[str, str]

class EnvironmentAuditor:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def audit(self) -> AuditResult:
        from datetime import datetime, timezone
        
        # 1. Shell detection
        shell = os.environ.get('SHELL', 'unknown')
        
        # 2. Python & Venv
        major, minor = sys.version_info.major, sys.version_info.minor
        python_version = f"{major}.{minor}"
        in_venv = sys.prefix != sys.base_prefix
        
        # 3. PATH analysis
        path_entries = os.environ.get('PATH', '').split(os.pathsep)
        
        # 4. Dependency checks
        node_present = shutil.which('node') is not None
        npm_present = shutil.which('npm') is not None
        
        docker_path = shutil.which('docker')
        docker_present = docker_path is not None
        docker_running = False
        if docker_present:
            try:
                subprocess.run(['docker', 'info'], capture_output=True, check=True)
                docker_running = True
            except Exception:
                docker_running = False
                
        # 5. Relevant Env Vars
        interesting_vars = [
            'LIBRARIAN_HOME', 'LIBRARIAN_STORAGE_PATH', 'LIBRARIAN_LOG_DIR',
            'PATH', 'PYTHONPATH', 'NODE_PATH'
        ]
        env_snapshot = {v: os.environ.get(v, '') for v in interesting_vars if v in os.environ}

        return AuditResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            shell=shell,
            python_version=python_version,
            in_venv=in_venv,
            path_entries=path_entries,
            node_present=node_present,
            npm_present=npm_present,
            docker_present=docker_present,
            docker_running=docker_running,
            platforms=platform.platform(),
            env_vars=env_snapshot
        )

def run_audit(root_dir: Path) -> dict:
    auditor = EnvironmentAuditor(root_dir)
    return asdict(auditor.audit())

if __name__ == "__main__":
    # Portable root detection
    root = Path(__file__).parent.parent.resolve()
    result = run_audit(root)
    print(json.dumps(result, indent=2))
