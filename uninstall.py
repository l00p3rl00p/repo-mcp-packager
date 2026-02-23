#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _is_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _interactive_args() -> list[str]:
    print("\nWorkforce Nexus — Uninstall / Purge (interactive)")
    print("----------------------------------------------")
    print("Pick an option:")
    print("  1) Preview: Env reset (safe)    [dry-run]")
    print("  2) Apply:   Env reset (safe)    [requires PURGE]")
    print("  3) Preview: Full wipe (pristine)[dry-run]")
    print("  4) Apply:   Full wipe (pristine)[requires PURGE]")
    print("  5) Preview: Detach clients only [dry-run]")
    print("  6) Apply:   Detach clients only [requires PURGE]")
    print("  q) Quit")
    choice = input("\nChoice: ").strip().lower()
    if choice in ("q", "quit", "exit"):
        return []

    detach_all = [
        "--detach-clients",
        "--detach-managed-servers",
        "--detach-suite-tools",
        "--remove-path-block",
        "--remove-wrappers",
    ]

    if choice == "1":
        return ["--purge-env", *detach_all, "--dry-run"]
    if choice == "2":
        confirm = input("Type PURGE to proceed: ").strip()
        if confirm != "PURGE":
            print("Aborted.")
            return []
        return ["--purge-env", *detach_all, "--yes"]
    if choice == "3":
        return ["--purge-data", "--kill-venv", *detach_all, "--dry-run"]
    if choice == "4":
        confirm = input("Type PURGE to proceed: ").strip()
        if confirm != "PURGE":
            print("Aborted.")
            return []
        return ["--purge-data", "--kill-venv", *detach_all, "--yes"]
    if choice == "5":
        return ["--detach-clients", "--detach-managed-servers", "--detach-suite-tools", "--dry-run"]
    if choice == "6":
        confirm = input("Type PURGE to proceed: ").strip()
        if confirm != "PURGE":
            print("Aborted.")
            return []
        return ["--detach-clients", "--detach-managed-servers", "--detach-suite-tools", "--yes"]

    print("Invalid choice.")
    return []


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

    # If no meaningful flags were provided, offer an interactive picker.
    if not any(
        [
            ns.kill_venv,
            ns.purge_data,
            ns.purge_env,
            ns.detach_clients,
            ns.detach_managed_servers,
            ns.detach_suite_tools,
            ns.remove_path_block,
            ns.remove_wrappers,
            ns.yes,
            ns.dry_run,
        ]
    ):
        if _is_tty():
            picked = _interactive_args()
            if not picked:
                return 0
            # Re-parse picked flags through the same forwarding logic.
            ns, passthrough = parser.parse_known_args(picked)
        else:
            print("FAIL: uninstall requires flags when stdin is not a TTY.")
            print("Tip: run with one of:")
            print("  --purge-env ... --dry-run   (preview)")
            print("  --purge-data ... --dry-run  (preview)")
            print("Or run it from a terminal for interactive mode.")
            return 2

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
