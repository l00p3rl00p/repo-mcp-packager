#!/usr/bin/env python3
"""
MCP Bridge Generator - Wrap legacy code as MCP servers

This tool scans legacy automation scripts and generates MCP server wrappers
that expose their functionality to AI assistants (Claude, Xcode, Cursor, etc.)

Usage:
    python bridge.py --scan           # Discover tools in current directory
    python bridge.py --generate       # Generate MCP wrapper
    python bridge.py --attach         # Attach to IDEs (requires mcp_injector)
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Soft dependency on mcp_injector (graceful degradation)
try:
    # Try to import from parent directory (root)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_injector import MCPInjector
    INJECTOR_AVAILABLE = True
except ImportError:
    INJECTOR_AVAILABLE = False
    MCPInjector = None


@dataclass
class LegacyTool:
    """Represents a discovered legacy automation entry point"""
    name: str
    source_file: Path
    entry_point: str  # Function name or "main"
    description: str
    arg_spec: Dict[str, str]  # {arg_name: type_hint}


class MCPBridgeGenerator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.discovered_tools: List[LegacyTool] = []
    
    def log(self, msg: str):
        """Simple logging"""
        print(f"[Bridge] {msg}")
    
    def discover_tools(self) -> List[LegacyTool]:
        """
        Scan project for executable entry points.
        Currently supports Python scripts with __main__ blocks.
        """
        self.log(f"Scanning {self.project_root} for legacy tools...")
        
        tools = []
        
        # Find Python scripts
        for py_file in self.project_root.rglob("*.py"):
            # Skip generated files and installers
            if py_file.name in ["mcp_server.py", "install.py", "uninstall.py", "bridge.py"]:
                continue
            
            # Check for __main__ block
            content = py_file.read_text()
            if 'if __name__ == "__main__"' in content:
                tool = self._analyze_python_script(py_file, content)
                if tool:
                    tools.append(tool)
        
        self.discovered_tools = tools
        self.log(f"Found {len(tools)} tools")
        return tools
    
    def _analyze_python_script(self, script_path: Path, content: str) -> Optional[LegacyTool]:
        """Extract metadata from a Python script"""
        # Look for main() function or direct execution
        name = script_path.stem
        
        # Try to find a docstring
        description = "Auto-detected legacy script"
        if '"""' in content:
            start = content.find('"""') + 3
            end = content.find('"""', start)
            if end > start:
                description = content[start:end].strip().split('\n')[0]
        
        # For now, assume simple CLI with sys.argv
        # Future: parse argparse/optparse
        return LegacyTool(
            name=name,
            source_file=script_path,
            entry_point="main",
            description=description,
            arg_spec={}  # Will be enhanced in future phases
        )
    
    def generate_bridge(self, server_name: Optional[str] = None) -> Path:
        """
        Generate an MCP server wrapper for discovered tools.
        Returns the path to the generated mcp_server.py file.
        """
        if not self.discovered_tools:
            self.discover_tools()
        
        if not self.discovered_tools:
            self.log("No tools discovered. Nothing to wrap.")
            return None
        
        server_name = server_name or self.project_root.name
        
        self.log(f"Generating MCP bridge for {len(self.discovered_tools)} tools...")
        
        # Generate the bridge code
        bridge_code = self._generate_bridge_code(server_name, self.discovered_tools)
        
        # Write to mcp_server.py
        output_path = self.project_root / "mcp_server.py"
        output_path.write_text(bridge_code)
        
        self.log(f"✅ Created {output_path}")
        return output_path
    
    def _generate_bridge_code(self, server_name: str, tools: List[LegacyTool]) -> str:
        """Generate the Python code for the MCP server wrapper"""
        
        # Generate tool functions
        tool_functions = []
        for tool in tools:
            func_code = f'''
@server.tool()
def {tool.name}(*args) -> str:
    """{tool.description}"""
    import subprocess
    result = subprocess.run(
        [sys.executable, "{tool.source_file.relative_to(self.project_root)}"] + list(args),
        capture_output=True,
        text=True,
        cwd="{self.project_root}"
    )
    return result.stdout if result.returncode == 0 else f"Error: {{result.stderr}}"
'''
            tool_functions.append(func_code)
        
        # Assemble the full server
        bridge_template = f'''#!/usr/bin/env python3
"""
MCP Server - Auto-generated bridge for legacy tools
Server: {server_name}
Tools: {", ".join(t.name for t in tools)}
"""

import sys
from pathlib import Path

# MCP Server implementation
# Note: This is a minimal implementation for demonstration
# Real implementation should use the official MCP Python SDK

class Server:
    def __init__(self, name):
        self.name = name
        self.tools = {{}}
    
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    def run(self):
        print(f"MCP Server '{{self.name}}' running with tools: {{list(self.tools.keys())}}")
        # In real implementation, this would start the MCP protocol server

server = Server("{server_name}")

{''.join(tool_functions)}

if __name__ == "__main__":
    server.run()
'''
        
        return bridge_template
    
    def offer_attachment(self):
        """
        Offer to attach the generated MCP server to user's IDEs.
        Uses mcp_injector if available, otherwise shows manual instructions.
        """
        if not INJECTOR_AVAILABLE:
            self._print_manual_instructions()
            return
        
        print("\n" + "="*50)
        print("🔌 MCP Injector detected!")
        print("="*50)
        print("Would you like to auto-attach this server to your IDEs?")
        print("(Claude, Xcode, Cursor, etc.)")
        print("")
        
        choice = input("Auto-attach? [Y/n]: ").strip().lower()
        
        if choice == 'n':
            self._print_manual_instructions()
            return
        
        # Use injector to attach
        try:
            # Detect which clients are available
            injector = MCPInjector(config_path=None)  # Will auto-detect
            clients = injector.detect_clients() if hasattr(injector, 'detect_clients') else {}
            
            if not clients:
                self.log("⚠️  No MCP-compatible IDEs found")
                self._print_manual_instructions()
                return
            
            self.log(f"Found IDEs: {', '.join(clients.keys())}")
            
            # For now, just print what would happen
            # Full implementation in Phase 2
            self.log("✅ Attachment logic will be implemented in Phase 2")
            self.log("For now, use: python mcp_injector.py --add")
            
        except Exception as e:
            self.log(f"⚠️  Auto-attach failed: {e}")
            self._print_manual_instructions()
    
    def _print_manual_instructions(self):
        """Fallback: print manual configuration instructions"""
        print("\n" + "="*50)
        print("📋 Manual Setup Instructions")
        print("="*50)
        print("")
        print("1. Add this server to your IDE config:")
        print(f'   {{')
        print(f'     "{self.project_root.name}": {{')
        print(f'       "command": "python",')
        print(f'       "args": ["{self.project_root / "mcp_server.py"}"]')
        print(f'     }}')
        print(f'   }}')
        print("")
        print("2. Or use the MCP injector:")
        print(f"   python mcp_injector.py --client claude --add")
        print("")
        print(f"3. See MCP_MANUAL_CONFIG.md for detailed IDE config locations")
        print("")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Bridge Generator")
    parser.add_argument("--scan", action="store_true", help="Scan for legacy tools")
    parser.add_argument("--generate", action="store_true", help="Generate MCP bridge")
    parser.add_argument("--attach", action="store_true", help="Attach to IDEs (requires mcp_injector)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root directory")
    
    args = parser.parse_args()
    
    generator = MCPBridgeGenerator(args.project_root)
    
    if args.scan:
        tools = generator.discover_tools()
        if tools:
            print(f"\n📋 Discovered {len(tools)} tools:\n")
            for tool in tools:
                print(f"  • {tool.name}")
                print(f"    Source: {tool.source_file.relative_to(args.project_root)}")
                print(f"    Description: {tool.description}")
                print()
        else:
            print("No legacy tools found.")
    
    elif args.generate:
        bridge_path = generator.generate_bridge()
        if bridge_path:
            print(f"\n✅ MCP bridge generated: {bridge_path}")
            
            if args.attach:
                generator.offer_attachment()
    
    elif args.attach:
        generator.offer_attachment()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
