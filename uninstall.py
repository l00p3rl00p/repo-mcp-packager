#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall MCP Workforce Nexus (repo entrypoint)")
    parser.add_argument("--kill-venv", action="store_true", help="Remove the local .venv (if present)")
    parser.add_argument("--purge-data", action="store_true", help="Purge shared Nexus data (~/.mcp-tools and ~/.mcpinv)")
    ns, passthrough = parser.parse_known_args()

    script = Path(__file__).resolve().parent / "serverinstaller" / "uninstall.py"
    forwarded = []
    if ns.kill_venv:
        forwarded.append("--kill-venv")
    if ns.purge_data:
        forwarded.append("--purge-data")
    forwarded.extend(passthrough)
    return subprocess.run([sys.executable, str(script), *forwarded], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

