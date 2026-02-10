# Manual MCP Server Configuration Guide

**When to use this**: If the installer can't auto-attach, or you want to manually add an MCP server to your IDE.

---

## Step 1: Find Your Config File

| IDE | Config File Location (macOS) |
|-----|------------------------------|
| **Xcode 26.3** | `~/Library/Developer/Xcode/UserData/MCPServers/config.json` |
| **Codex App** | `~/Library/Application Support/Codex/mcp_servers.json` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Cursor** | `~/.cursor/mcp.json` |
| **VS Code** | `~/.vscode/mcp_settings.json` |

---

## Step 2: Check If File Exists

**Open Terminal and run:**
```bash
# Example for Claude Desktop
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Scenario A: File is Empty or Doesn't Exist
Start with this template:
```json
{
  "mcpServers": {
    "YOUR-SERVER-NAME": {
      "command": "COMMAND-HERE",
      "args": ["ARG1", "ARG2"]
    }
  }
}
```

### Scenario B: File Already Has Entries
You'll see something like:
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "npx",
      "args": ["-y", "some-package"]
    }
  }
}
```

---

## Step 3: Add Your New Server (The Tricky Part)

### ✅ CORRECT: Adding a Second Server

**BEFORE (one server):**
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "npx",
      "args": ["-y", "some-package"]
    }
  }
}
```

**AFTER (two servers):**
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "npx",
      "args": ["-y", "some-package"]
    },
    "agent-browser": {
      "command": "npx",
      "args": ["-y", "@vercel/agent-browser", "mcp"]
    }
  }
}
```

**Key Rules:**
1. Add a **comma** after the closing `}` of the previous entry
2. NO comma after the last entry
3. Keep the same indentation level

---

## Step 4: Fill-in-the-Blank Template

**Copy this and replace the ALL-CAPS placeholders:**

```json
{
  "mcpServers": {
    "EXISTING-SERVER-NAME-1": {
      "command": "EXISTING-COMMAND",
      "args": ["EXISTING-ARGS"]
    },
    "YOUR-NEW-SERVER-NAME": {
      "command": "YOUR-COMMAND",
      "args": ["YOUR-ARG-1", "YOUR-ARG-2"],
      "env": {
        "OPTIONAL-API-KEY": "your-key-here"
      }
    }
  }
}
```

### Example Values for Common Servers:

| Server | Name | Command | Args |
|--------|------|---------|------|
| **Agent Browser** | `agent-browser` | `npx` | `["-y", "@vercel/agent-browser", "mcp"]` |
| **Shesha/Librarian** | `shesha` | `/path/to/.venv/bin/librarian` | `["mcp", "run"]` |
| **NotebookLM** | `notebooklm` | `npx` | `["-y", "notebooklm-mcp-cli"]` |
| **AI Studio** | `aistudio` | `npx` | `["-y", "aistudio-mcp-server"]` |

---

## Step 5: Validate Your JSON

**Common Mistakes:**

❌ **Missing Comma Between Entries:**
```json
{
  "mcpServers": {
    "server-1": { ... }    ← Missing comma!
    "server-2": { ... }
  }
}
```

❌ **Extra Comma After Last Entry:**
```json
{
  "mcpServers": {
    "server-1": { ... },
    "server-2": { ... },   ← Remove this comma!
  }
}
```

❌ **Mismatched Brackets:**
```json
{
  "mcpServers": {
    "server-1": {
      "command": "npx"
    }    ← Missing closing bracket for mcpServers
}
```

**Validation Tool:**
```bash
# Check if your JSON is valid
cat ~/path/to/config.json | python3 -m json.tool
```
If you see an error, the JSON is broken. If it prints the formatted JSON, you're good!

---

## Step 6: Restart Your IDE

After saving the config file:
1. **Quit** your IDE completely (not just close the window)
2. **Reopen** the IDE
3. **Verify** the server appears in the MCP tools list

---

## Quick Reference: Complete Example

**Three servers in one config (Claude Desktop):**

```json
{
  "mcpServers": {
    "shesha": {
      "command": "/Users/you/projects/shesha/.venv/bin/librarian",
      "args": ["mcp", "run"]
    },
    "agent-browser": {
      "command": "npx",
      "args": ["-y", "@vercel/agent-browser", "mcp"]
    },
    "aistudio": {
      "command": "npx",
      "args": ["-y", "aistudio-mcp-server"],
      "env": {
        "GEMINI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Notice:**
- Commas after `shesha` and `agent-browser` entries
- NO comma after `aistudio` (the last entry)
- Consistent 2-space indentation

---

## Troubleshooting

### "MCP server not showing up"
1. Check JSON syntax with `python3 -m json.tool`
2. Verify the command path exists: `which npx` or `ls /path/to/command`
3. Restart IDE completely
4. Check IDE logs for errors

### "Permission denied" errors
```bash
# Make the command executable (for local scripts)
chmod +x /path/to/your/mcp/server
```

### "Command not found"
```bash
# For npx-based servers, ensure Node.js is installed
which npx
# If not found:
brew install node
```

---

## Need Help?

If manual configuration fails, use the automated installer:
```bash
python serverinstaller/install.py --attach-to <ide-name>
```

The installer handles all the bracket/comma logic automatically.
