import os
from pathlib import Path

output_file = Path("RED_TEAM_MASTER_BUILD_AUDIT.md")
search_dir = Path("/Users/almowplay/Developer/Github/mcp-creater-manager")

with open(output_file, "w", encoding="utf-8") as out:
    out.write("# RED TEAM MASTER BUILD AUDIT\n\n")
    out.write("This file aggregates all `AI-SDK-PROD-BUILD*.md` contracts across the main repository AND ALL sub-repositories for a comprehensive Red Team review.\n\n")
    out.write("---\n\n")
    
    # Grab all build contracts recursively across all repo folders
    files = list(search_dir.rglob("AI-SDK-PROD-BUILD*.md"))
    files.sort(key=lambda x: str(x))
    
    for f in files:
        if f.name == output_file.name:
            continue
            
        rel_path = f.relative_to(search_dir)
        out.write(f"## Contract File: `{rel_path}`\n\n")
        
        try:
            content = f.read_text(encoding="utf-8")
            out.write(content)
            out.write("\n\n---\n\n")
        except Exception as e:
            out.write(f"> **Error reading file:** {e}\n\n---\n\n")

print(f"Master file created at: {output_file.absolute()}")
