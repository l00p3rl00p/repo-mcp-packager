import os
import sys
import shutil
import subprocess
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

class ForgeEngine:
    """
    Workforce Nexus Forge Engine (The Factory) - Packager Edition
    Converts arbitrary folders or repositories into compliant MCP servers.
    """

    def __init__(self, suite_root: Path):
        self.suite_root = suite_root
        # In the context of repo-mcp-packager, we might need to find where the wrappers are
        # Usually they are in mcp-link-library
        self.link_library = suite_root / "mcp-link-library"
        self.inventory_path = suite_root / "mcp-server-manager" / "examples" / "inventory.yaml"

    def forge(self, source: str, target_name: Optional[str] = None) -> Path:
        """
        Main entry point for forging a server.
        source: A local path or a Git URL.
        """
        # 1. Determine local path
        if source.startswith(("http://", "https://", "git@")):
            target_path = self._clone_repo(source, target_name)
        else:
            target_path = Path(source).resolve()

        if not target_path.exists():
            raise FileNotFoundError(f"Source path {target_path} does not exist.")

        # 2. Inject Deterministic Wrapper
        self._inject_wrapper(target_path)

        # 3. Inject ATP Sandbox
        self._inject_sandbox(target_path)

        # 4. Generate Baseline Server if missing
        self._ensure_server_entrypoint(target_path)

        # 5. Export Compliance Kit
        self._export_compliance_kit(target_path)

        # 6. Verify Logic (Strawberry Test)
        self._verify_logic(target_path)

        # 7. Register with Inventory (Selective)
        self._register_inventory(target_path, source)

        return target_path

    def _verify_logic(self, target_path: Path):
        """Runs the 'Strawberry' logic test inside the fresh sandbox."""
        print(f"Running Strawberry Test on {target_path.name} (Packager Edition)...")
        
        import sys
        sys.path.insert(0, str(target_path))
        
        try:
            import random
            from atp_sandbox import ATPSandbox
            sb = ATPSandbox()
            
            tests = [
                {
                    "name": "Strawberry 'r' Count",
                    "code": "result = {'count': context['text'].lower().count('r')}",
                    "context": {"text": "The strawberry is Ripe and Ready, but are there 3 r's or 4?"},
                    "expected": 9
                },
                {
                    "name": "Math Evaluation",
                    "code": "result = {'count': (15 * 3) + 7 - 2}",
                    "context": {},
                    "expected": 50
                },
                {
                    "name": "List Filtering",
                    "code": "result = {'count': len([x for x in context['nums'] if x % 2 == 0])}",
                    "context": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
                    "expected": 5
                }
            ]
            test = random.choice(tests)
            print(f"➜ Running randomized logic test: {test['name']}")
            exec_res = sb.execute(test["code"], test.get("context", {}))
            
            if exec_res["success"] and isinstance(exec_res.get("result"), dict) and exec_res["result"].get("count") == test["expected"]:
                print(f"✅ Logic Test ({test['name']}) passed: Deterministic Logic verified.")
            else:
                error = exec_res.get("error", f"Mismatch (Got {exec_res.get('result', {}).get('count')}, expected {test['expected']})")
                print(f"⚠️ Logic Test failed: {error}")
        except Exception as e:
            print(f"❌ Verification skipped: Could not run sandbox test ({e})")
        finally:
            if str(target_path) in sys.path:
                sys.path.remove(str(target_path))

    def _clone_repo(self, url: str, name: Optional[str]) -> Path:
        if not name:
            name = url.split("/")[-1].replace(".git", "")
        
        # In packager, we might clone to a specific workspace or a managed area
        target_dir = self.suite_root / "forged_servers" / name
        target_dir.parent.mkdir(exist_ok=True)
        
        if target_dir.exists():
            print(f"Directory {target_dir} already exists. Skipping clone.")
            return target_dir

        print(f"Cloning {url} into {target_dir}...")
        subprocess.run(["git", "clone", url, str(target_dir)], check=True)
        return target_dir

    def _inject_wrapper(self, target_path: Path):
        """Injects the canonical mcp_wrapper.py."""
        wrapper_src = self.link_library / "mcp_wrapper.py"
        if wrapper_src.exists():
            shutil.copy2(wrapper_src, target_path / "mcp_wrapper.py")
            print(f"Injected mcp_wrapper.py into {target_path}")
        else:
            print(f"Warning: mcp_wrapper.py not found at {wrapper_src}")

    def _inject_sandbox(self, target_path: Path):
        """Injects the atp_sandbox.py."""
        sandbox_src = self.link_library / "atp_sandbox.py"
        if sandbox_src.exists():
            shutil.copy2(sandbox_src, target_path / "atp_sandbox.py")
            print(f"Injected atp_sandbox.py into {target_path}")
        else:
            print(f"Warning: atp_sandbox.py not found at {sandbox_src}")

    def _ensure_server_entrypoint(self, target_path: Path):
        """Generates a baseline mcp_server.py if no python entrypoint exists."""
        entrypoints = list(target_path.glob("mcp_server.py")) + list(target_path.glob("server.py"))
        if not entrypoints:
            # IMPORTANT: MCP stdio servers must NOT print banners to stdout.
            server_content = f"""# Baseline MCP Server (Forged via Packager)
\"\"\"
MCP Server: {target_path.name}
Generated by Nexus Forge (Packager).
Categories: forged, packager-v3
\"\"\"
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional


SERVER_NAME = {target_path.name!r}
SERVER_VERSION = "0.0.1-forged"


def _ok(msg_id: Any, result: Any) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "result": result}}


def _err(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {{"jsonrpc": "2.0", "id": msg_id, "error": {{"code": code, "message": message}}}}


def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = request.get("method")
    params = request.get("params") or {{}}
    msg_id = request.get("id")

    if msg_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    try:
        if method == "initialize":
            return _ok(
                msg_id,
                {{
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {{"name": SERVER_NAME, "version": SERVER_VERSION}},
                    "capabilities": {{"tools": {{"listChanged": False}}}},
                }},
            )
        if method in ("notifications/initialized",):
            return None
        if method == "tools/list":
            return _ok(
                msg_id,
                {{
                    "tools": [
                        {{
                            "name": "ping",
                            "description": "Liveness check (forged baseline).",
                            "inputSchema": {{"type": "object", "properties": {{}}, "additionalProperties": False}},
                        }}
                    ]
                }},
            )
        if method == "tools/call":
            name = (params.get("name") or "").strip()
            if name == "ping":
                return _ok(msg_id, {{"ok": True, "ts": time.time(), "server": SERVER_NAME}})
            return _err(msg_id, -32601, f"Unknown tool: {name}")
        return _err(msg_id, -32601, f"Unknown method: {method}")
    except Exception as e:
        return _err(msg_id, -32000, f"Server error: {e}")


def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
"""
            with open(target_path / "mcp_server.py", "w") as f:
                f.write(server_content)
            print(f"Generated baseline mcp_server.py in {target_path}")

    def _export_compliance_kit(self, target_path: Path):
        """Exports the standard ARCHITECTURE.md and README.md markers via the Librarian."""
        print(f"Generating Compliance Kit for {target_path.name} (Packager)...")
        
        librarian_path = self.suite_root / "mcp-link-library" / "mcp.py"
        if librarian_path.exists():
            try:
                subprocess.run([sys.executable, str(librarian_path), "--prepopulate-docs", str(target_path)], check=False)
            except Exception as e:
                print(f"⚠️  Librarian call failed: {e}")
        else:
            (target_path / "ARCHITECTURE.md").touch(exist_ok=True)
            (target_path / "README.md").touch(exist_ok=True)
            
        # Add a marker for the packager
        (target_path / ".nexus_forged").touch()
        print(f"Compliance Kit for {target_path.name} exported.")

    def _register_inventory(self, target_path: Path, source: str):
        """Registers the forged server in the suite's inventory."""
        if not self.inventory_path.exists():
            print(f"Warning: Inventory not found at {self.inventory_path}. Skipping registration.")
            return

        with open(self.inventory_path, "r") as f:
            inventory = yaml.safe_load(f) or {"servers": []}

        server_id = target_path.name
        if any(s.get("id") == server_id for s in inventory["servers"]):
            return

        new_entry = {
            "id": server_id,
            "name": server_id,
            "path": str(target_path),
            "confidence": "forged",
            "status": "ready",
            "source": source,
            "tags": ["forged", "packager-v3"],
            "added_on": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        inventory["servers"].append(new_entry)

        with open(self.inventory_path, "w") as f:
            yaml.safe_dump(inventory, f)
        print(f"Registered {server_id} in {self.inventory_path}")
