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
    parser.add_argument("--purge-env", action="store_true", help="Purge only shared environments (~/.mcp-tools/.venv and per-server envs)")
    parser.add_argument("--detach-clients", action="store_true", help="Remove Nexus suite servers from detected IDE clients")
    parser.add_argument("--detach-managed-servers", action="store_true", help="Detach managed servers (e.g., ~/.mcp-tools/servers/*) from clients")
    parser.add_argument("--detach-suite-tools", action="store_true", help="Detach suite tools (nexus-*) from clients")
    parser.add_argument("--remove-path-block", action="store_true", help="Remove PATH injection block from shell rc files")
    parser.add_argument("--remove-wrappers", action="store_true", help="Remove user wrapper scripts (e.g., ~/.local/bin/mcp-*)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--devlog", action="store_true", help="Write dev log (JSONL) with 90-day retention")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts (DANGEROUS)")
    parser.add_argument("--dry-run", action="store_true", help="Print planned removals, but do not delete anything")
    ns, passthrough = parser.parse_known_args()

    script = Path(__file__).resolve().parent / "serverinstaller" / "uninstall.py"
    forwarded = []
    if ns.kill_venv:
        forwarded.append("--kill-venv")
    if ns.purge_data:
        forwarded.append("--purge-data")
    if ns.purge_env:
        forwarded.append("--purge-env")
    if ns.detach_clients:
        forwarded.append("--detach-clients")
    if ns.detach_managed_servers:
        forwarded.append("--detach-managed-servers")
    if ns.detach_suite_tools:
        forwarded.append("--detach-suite-tools")
    if ns.remove_path_block:
        forwarded.append("--remove-path-block")
    if ns.remove_wrappers:
        forwarded.append("--remove-wrappers")
    if ns.verbose:
        forwarded.append("--verbose")
    if ns.devlog:
        forwarded.append("--devlog")
    if ns.yes:
        forwarded.append("--yes")
    if ns.dry_run:
        forwarded.append("--dry-run")
    forwarded.extend(passthrough)
    return subprocess.run([sys.executable, str(script), *forwarded], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
