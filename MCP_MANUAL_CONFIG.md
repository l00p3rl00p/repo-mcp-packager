# Manual MCP Server Configuration Guide

This guide provides step-by-step instructions on how to manually add an MCP server to your IDE if the automated installer cannot be used.

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Step 1: Find Your Config File](#-step-1-find-your-config-file)
3. [Step 2: Check Existing Config](#-step-2-check-existing-config)
4. [Step 3: Add Your Server](#-step-3-add-your-server)
5. [Step 4: Common Server Templates](#-step-4-common-server-templates)
6. [Step 5: Validate Your JSON](#-step-5-validate-your-json)
7. [Verification & Troubleshooting](#-verification--troubleshooting)

---

## 🔍 Prerequisites

* Access to your machine's filesystem.
* A text editor (VS Code, Cursor, or even TextEdit).
* Basic understanding of JSON structure (or just follow the templates below).

---

## 📂 Step 1: Find Your Config File

Different IDEs store their MCP configurations in specific locations.

| IDE | Config File Location (macOS) |
|-----|------------------------------|
| **Xcode 26.3** | `~/Library/Developer/Xcode/UserData/MCPServers/config.json` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Codex App** | `~/Library/Application Support/Codex/mcp_servers.json` |
| **Cursor** | `~/.cursor/mcp.json` |
| **VS Code** | `~/.vscode/mcp_settings.json` |

---

## 🔍 Step 2: Check Existing Config

Before editing, see if the file already exists and what it contains.

**Open Terminal and run:**
```bash
# Example for Claude Desktop
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Case A: File is Empty or New
If the file doesn't exist, you'll start with this base structure:
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

## 🛠 Step 3: Add Your Server

This is where most mistakes happen. Follow the "Comma Rule" strictly.

### ✅ Adding a Second Server

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

> **The Golden Rules of JSON:**
> 1. Add a **comma** `,` after every entry EXCEPT the last one in a list or object.
> 2. Ensure every opening `{` or `[` has a matching closing `}` or `]`.

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

## ✅ Step 5: Validate Your JSON

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
cat ~/path/to/config.json | python3 -m json.tool
```
* **Success**: It prints the formatted JSON.
* **Failure**: It shows a `JSONDecodeError`. Fix the syntax before proceeding.

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

---

## Startup Auto-Detect (Recommended)

The injector now supports startup discovery for common MCP-capable IDEs and prompts before injection.

```bash
python mcp_injector.py --startup-detect
```

Behavior:
* Detects common clients (`claude`, `codex`, `cursor`, `vscode`, `xcode`, `aistudio`, `google-antigravity`).
* Always includes **Claude** in the prompt set as a common injection target.
* If the full Nexus package is detected (`~/.mcp-tools/bin`), it offers injection only for **MCP-server** components (currently `nexus-librarian`). Other Nexus binaries like `mcp-activator` are CLIs and should not be injected into MCP clients.
* For each component, injection is explicit: **inject now** or **skip now**.

---

## Web Clients (Recommended Pattern)
If you want MCP tools inside **browser-based AI clients** (ChatGPT, Perplexity, Gemini, AI Studio, etc.), the most reliable pattern is to run a local MCP proxy that exposes SSE/HTTP/WS endpoints (adds CORS, health endpoints, etc.) and then connect the web client/extension to that proxy.

Example (SSE) using a local MCP proxy:
```bash
<your-mcp-proxy> --config "~/Library/Application Support/Claude/claude_desktop_config.json" --outputTransport sse
```

---

## Supported Injection Schema (Best Practice)
For IDE/Desktop MCP clients (Claude Desktop, Codex, Cursor, VS Code, Xcode), the safe/typical shape under `mcpServers` is:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "OPTIONAL_KEY": "optional_value"
      }
    }
  }
}
```
Notes:
* `command` must be a single executable.
* `args` should be an array (strings).
* Avoid injecting non-server CLIs (e.g. `mcp-activator`, `mcp-observer`, `mcp-surgeon`) as MCP servers.
