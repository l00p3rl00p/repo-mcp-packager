#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from forge_engine import ForgeEngine

def main():
    parser = argparse.ArgumentParser(description="repo-mcp-packager Forge (The Factory)")
    parser.add_argument("--dir", type=str, help="Local directory to forge")
    parser.add_argument("--repo", type=str, help="Remote Git repository to clone and forge")
    parser.add_argument("--name", type=str, help="Optional name for the forged server")
    
    args = parser.parse_args()

    # Determine suite root
    script_path = Path(__file__).resolve()
    # /repo-mcp-packager/forge/mcp-forge.py -> /mcp-creater-manager
    suite_root = script_path.parent.parent.parent
    
    engine = ForgeEngine(suite_root)

    try:
        source = args.repo if args.repo else args.dir
        if not source:
            parser.print_help()
            sys.exit(1)
            
        target = engine.forge(source, args.name)
        print(f"\nSUCCESS: Server forged and Nexus-Ready at: {target}")
    except Exception as e:
        print(f"\nERROR during forge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
