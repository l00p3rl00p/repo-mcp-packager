#!/usr/bin/env python3
"""
MCP Server Attachment Orchestrator

This module handles attaching MCP servers to IDE configurations.
It detects installed IDEs and delegates to MCPInjector for surgical JSON manipulation.

Usage:
    from attach import attach_to_clients, detect_clients
    
    # Detect available IDEs
    clients = detect_clients()
    
    # Attach server to all detected clients
    attach_to_clients({
        "name": "my-server",
        "command": "npx",
        "args": ["-y", "my-package"]
    })
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import MCPInjector from root (soft dependency handled in bridge.py)
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_injector import MCPInjector, KNOWN_CLIENTS
    INJECTOR_AVAILABLE = True
except ImportError:
    INJECTOR_AVAILABLE = False
    MCPInjector = None
    KNOWN_CLIENTS = {}


@dataclass
class AttachmentResult:
    """Result of attaching an MCP server to clients"""
    client_name: str
    config_path: Path
    server_name: str
    success: bool
    error: Optional[str] = None


def detect_clients() -> Dict[str, Path]:
    """
    Detect which MCP-compatible IDEs are installed.
    
    Returns:
        Dict mapping client name to config file path
        Example: {"claude": Path("~/Library/.../claude_desktop_config.json")}
    """
    if not INJECTOR_AVAILABLE:
        print("⚠️  MCPInjector not available. Cannot detect clients.")
        return {}
    
    found = {}
    for name, config_path_str in KNOWN_CLIENTS.items():
        config_path = Path(config_path_str).expanduser()
        if config_path.exists() or config_path.parent.exists():
            # Include if config exists OR parent dir exists (we can create config)
            found[name] = config_path
    
    return found


def attach_to_clients(
    server_config: Dict[str, Any],
    client_names: Optional[List[str]] = None,
    interactive: bool = True
) -> List[AttachmentResult]:
    """
    Attach MCP server to one or more IDE configs.
    
    Args:
        server_config: {
            "name": "server-name",
            "command": "npx",
            "args": ["-y", "package-name"],
            "env": {"KEY": "value"}  # optional
        }
        client_names: List of clients to attach to, or None for all detected
        interactive: If True, prompt before each attachment
    
    Returns:
        List of AttachmentResult objects
    """
    if not INJECTOR_AVAILABLE:
        print("❌ MCPInjector not available. Cannot attach to clients.")
        print("   Ensure mcp_injector.py is in the parent directory.")
        return []
    
    # Detect available clients
    available_clients = detect_clients()
    
    if not available_clients:
        print("⚠️  No MCP-compatible IDEs detected.")
        return []
    
    # Determine which clients to attach to
    if client_names is None:
        # Attach to all detected
        targets = available_clients
    else:
        # Filter to requested clients
        targets = {
            name: path 
            for name, path in available_clients.items() 
            if name in client_names
        }
    
    if not targets:
        print(f"⚠️  None of the requested clients are installed: {client_names}")
        return []
    
    # Show what will be attached
    print("\n" + "="*50)
    print(f"🔌 Attaching MCP Server: {server_config['name']}")
    print("="*50)
    print(f"Command: {server_config['command']}")
    print(f"Args: {' '.join(server_config['args'])}")
    print(f"\nTarget IDEs: {', '.join(targets.keys())}")
    print("="*50)
    
    # Interactive confirmation
    if interactive:
        response = input("\nProceed with attachment? [Y/n]: ").strip().lower()
        if response == 'n':
            print("❌ Attachment cancelled by user")
            return []
    
    # Perform attachments
    results = []
    
    for client_name, config_path in targets.items():
        result = _attach_to_single_client(
            client_name=client_name,
            config_path=config_path,
            server_config=server_config
        )
        results.append(result)
        
        # Print status
        if result.success:
            print(f"✅ {client_name}: Attached successfully")
        else:
            print(f"❌ {client_name}: {result.error}")
    
    # Summary
    success_count = sum(1 for r in results if r.success)
    print(f"\n📊 Attachment Summary: {success_count}/{len(results)} successful")
    
    return results


def _attach_to_single_client(
    client_name: str,
    config_path: Path,
    server_config: Dict[str, Any]
) -> AttachmentResult:
    """
    Attach MCP server to a single IDE config.
    Uses MCPInjector for the actual JSON manipulation.
    """
    try:
        # Create injector instance for this config
        injector = MCPInjector(config_path)
        
        # Extract server details
        name = server_config["name"]
        command = server_config["command"]
        args = server_config.get("args", [])
        env = server_config.get("env")
        
        # Use injector to add server
        injector.add_server(name, command, args, env)
        
        return AttachmentResult(
            client_name=client_name,
            config_path=config_path,
            server_name=name,
            success=True
        )
        
    except Exception as e:
        return AttachmentResult(
            client_name=client_name,
            config_path=config_path,
            server_name=server_config["name"],
            success=False,
            error=str(e)
        )


def remove_from_clients(
    server_name: str,
    client_configs: List[Dict[str, str]]
) -> List[AttachmentResult]:
    """
    Remove MCP server from IDE configs (used by uninstall.py).
    
    Args:
        server_name: Name of the server to remove
        client_configs: List of dicts with "name" and "config_path"
    
    Returns:
        List of AttachmentResult objects
    """
    if not INJECTOR_AVAILABLE:
        print("❌ MCPInjector not available. Cannot remove from clients.")
        return []
    
    results = []
    
    for client_info in client_configs:
        client_name = client_info["name"]
        config_path = Path(client_info["config_path"]).expanduser()
        
        try:
            if not config_path.exists():
                results.append(AttachmentResult(
                    client_name=client_name,
                    config_path=config_path,
                    server_name=server_name,
                    success=False,
                    error="Config file no longer exists"
                ))
                continue
            
            # Use injector to remove
            injector = MCPInjector(config_path)
            injector.remove_server(server_name)
            
            results.append(AttachmentResult(
                client_name=client_name,
                config_path=config_path,
                server_name=server_name,
                success=True
            ))
            
        except Exception as e:
            results.append(AttachmentResult(
                client_name=client_name,
                config_path=config_path,
                server_name=server_name,
                success=False,
                error=str(e)
            ))
    
    return results


def main():
    """CLI for testing attachment functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server Attachment Tool")
    parser.add_argument("--detect", action="store_true", help="Detect installed IDEs")
    parser.add_argument("--attach", metavar="SERVER_NAME", help="Server name to attach")
    parser.add_argument("--command", default="npx", help="Server command")
    parser.add_argument("--args", nargs="+", help="Server arguments")
    parser.add_argument("--clients", nargs="+", help="Specific clients (claude, xcode, etc.)")
    
    args = parser.parse_args()
    
    if args.detect:
        clients = detect_clients()
        if clients:
            print(f"\n📋 Detected {len(clients)} MCP-compatible IDE(s):\n")
            for name, path in clients.items():
                exists = "✓" if path.exists() else "⚠️  (config will be created)"
                print(f"  • {name}: {path} {exists}")
        else:
            print("No MCP-compatible IDEs found.")
    
    elif args.attach:
        if not args.args:
            print("❌ --args required for attachment")
            return
        
        server_config = {
            "name": args.attach,
            "command": args.command,
            "args": args.args
        }
        
        results = attach_to_clients(
            server_config,
            client_names=args.clients,
            interactive=True
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
