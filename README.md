# Git Repo MCP Converter & Installer

**A "Just Works" installation experience for converting any repository into an MCP-ready toolset.**

`repo-mcp-packager` provides automation for installing, packaging, and bridging existing code as MCP servers. It ensures clean, isolated environments across any repository fork.

---

## ⚡ Quick Start (60s)

### 1. Bootstrap Workspace
The recommended way to get started is by bootstrapping the full Git-Packager workspace:

```bash
python bootstrap.py
```

### 2. Manual Installation
Alternatively, run the installer directly in any repository:

```bash
python serverinstaller/install.py
```

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [MCP Bridge](#-mcp-bridge)
4. [Design Philosophy](#-design-philosophy)
5. [Key Arguments](#-key-arguments)
6. [Documentation](#-documentation)
7. [Git-Packager Workspace](#-git-packager-workspace)
8. [Standalone vs Integrated: Understanding the Trade-offs](#-standalone-vs-integrated-understanding-the-trade-offs)
9. [Contributing](#-contributing)
10. [License](#-license)

---

## 🔍 Overview

This project implements a portal installer that converts any repository into an MCP server. It is designed to be "entry point agnostic," meaning you can drop the `/serverinstaller` directory into any codebase and it will intelligently detect the environment and offer a clean path to deployment.

The converter handles Python, Node, and Docker services, providing a surgical reversal (uninstall) that leaves the host system exactly as it was found.

---

## 🌟 Features

* **Portability**: Standalone directory that bootstraps from host tools.
* **Inventory Awareness**: Probes and identifies components (Python, Node, Docker) automatically.
* **Surgical Reversal**: Marker-aware cleanup of Path and shell configurations.
* **MCP Bridge**: Converts legacy automation scripts into AI-accessible MCP tools.
* **Headless Mode**: Zero-touch replication for automated agents.

---

## 🌉 MCP Bridge

**Turn any legacy code into AI-accessible tools instantly:**

```bash
# Attach existing MCP server to your IDEs
python install.py --attach-to all

# Wrap legacy script + attach to Claude
python install.py --generate-bridge --attach-to claude

# Detect available IDEs
python attach.py --detect
```

The bridge generator scans your scripts for execution blocks and creates a wrapper that exposes functions as MCP tools.

---

## 💡 Philosophy: Not Every Repo Is a Product

The installer understands that code exists on a spectrum. It respects minimalism:
* **Respect Minimalism**: Don't force a `.venv` on a script that doesn't need one.
* **Offer Transition Paths**: Simple scripts can be "upgraded" to full packages later.
* **Enable Portability**: Whether it's a `.sh` wrapper or a full package, the result should be copy-pasteable.

> *"The best installer is the one that knows when to do nothing."*

---

## ⚙️ Key Arguments

| Flag | Description |
| --- | --- |
| `--headless` | Bypass all interactive prompts (agent mode). |
| `--no-gui` | Skip GUI/NPM installation phase. |
| `--npm-policy {local,global,auto}` | Control Node/NPM isolation. |
| `--docker-policy {skip,fail}` | Define behavior if Docker is missing. |

---

## 📚 Documentation

Detailed documentation is available in the following files:

* [USER_OUTCOMES.md](USER_OUTCOMES.md): Mission statement and success criteria.
* [ARCHITECTURE.md](ARCHITECTURE.md): Technical logic and internal modular design.
* [ENVIRONMENT.md](ENVIRONMENT.md): Requirements and audit logic.
* [CHANGELOG.md](CHANGELOG.md): History of improvements.

---

## 🤝 Git-Packager Workforce Suite

This tool is the **Activator (Deployer)** for the complete four-component workforce ecosystem:

| Tool | Persona | Purpose |
| --- | --- | --- |
| **mcp-injector** | The Surgeon | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | The Observer | Discover, track, and monitor health of all MCP servers |
| **repo-mcp-packager** | The Activator | Install, package, and update MCP servers with automation |
| **mcp-link-library** | The Librarian | Curated knowledge base and document engine for AI tools |

### Integrated Benefits
* **Universal Bootstrapping**: `bootstrap.py` aligns and fetches all 4 tools.
* **Lifecycle Management**: Automated `install.py --update` pulls code and refreshes knowledge.
* **Centralized Health**: Manager GUI tracks everything from Docker status to Librarian integrity.

---

## 🎯 Standalone vs Integrated: Understanding the Trade-offs

### Can This Tool Work Standalone?

**Yes**, but with significant limitations. This is the **orchestrator** of the suite—it's designed to convert repos into working MCP servers, but its full power emerges when integrated.

---

### 📊 Standalone Usage

**What you can do:**

- ✅ **Install any repo** with automatic environment detection
- ✅ **Create Python venvs** with correct dependencies
- ✅ **Setup Node/NPM** environments
- ✅ **Configure Docker** services
- ✅ **Generate MCP bridges** from legacy scripts
- ✅ **Clean uninstall** with surgical reversal
- ✅ **Headless mode** for automated deployments

**What you cannot do:**

- ❌ **Auto-configure IDEs** after install (requires `mcp-injector`)
- ❌ **Track installed servers** across your system (requires `mcp-server-manager`)
- ❌ **Know if server is already installed** elsewhere (requires `mcp-server-manager` inventory)
- ❌ **One-click "install everywhere"** (requires full suite)
- ❌ **Validate installation success** with running checks (requires `mcp-server-manager`)

**Best for:**

- Installing single repos in isolation
- Custom deployment pipelines
- CI/CD automation (headless mode)
- Teams with existing IDE configuration workflows
- Users who want full control over each step

---

### 🚀 Integrated Usage (Full Git-Packager Suite)

**What you gain with `mcp-injector`:**

- ✅ **Auto-configure IDE** immediately after successful install
- ✅ **One command: install → configure** (no manual IDE setup)
- ✅ **Correct paths automatically** (venv, Docker, Node)
- ✅ **Update IDE configs** when server is upgraded
- ✅ **Remove from IDE** when server is uninstalled

**What you gain with `mcp-server-manager`:**

- ✅ **Pre-install checks** - detect if server already exists
- ✅ **Post-install validation** - verify server responds
- ✅ **Inventory tracking** - know what's installed where
- ✅ **Prevent duplicates** - don't install same server twice
- ✅ **Health monitoring** - see if installed servers are working
- ✅ **GUI dashboard** - visual control of all installed servers

**Best for:**

- Building complete MCP ecosystems
- Teams managing multiple MCP servers
- Anyone who values "drop and run" simplicity
- Automated discovery → install → configure workflows
- Organizations standardizing MCP deployments

---

### 🤔 Decision Matrix

| Your Situation | Recommended Setup |
| --- | --- |
| "I need to install one repo as MCP server, that's it" | **Standalone** `repo-mcp-packager` |
| "I have CI/CD that installs servers" | **Standalone** `repo-mcp-packager` (headless) |
| "I want install + IDE config in one command" | **Add** `mcp-injector` |
| "I want to track all installed servers" | **Add** `mcp-server-manager` |
| "I want complete automation: discover → install → configure" | **Full suite** (all 3 tools) |
| "I'm building custom deployment automation" | **Standalone** `repo-mcp-packager` |

---

### 💡 Real-World Scenarios

**Scenario 1: Installing a single MCP server repo**

```bash
# Standalone works perfectly
cd /path/to/mcp-repo
python serverinstaller/install.py
# Server installed, but you manually add to IDE config
```

**Scenario 2: Installing multiple servers across projects**

```bash
# Without full suite: Install each one individually
cd project-a && python install.py
cd project-b && python install.py
cd project-c && python install.py
# Now manually configure each in IDE...

# With full suite: Orchestrated workflow
python bootstrap.py --scan-and-install ~/Developer
# Discovers all MCP repos, installs them, configures IDE
# Done in one command
```

**Scenario 3: Converting legacy repo to MCP server**

```bash
# Standalone can generate the bridge
python install.py --generate-bridge
# But you still manually add to IDE

# With mcp-injector integrated
python install.py --generate-bridge --attach-to claude
# Bridge generated AND IDE configured automatically
```

**Scenario 4: CI/CD pipeline**

```bash
# Standalone is perfect for headless automation
python install.py --headless --no-gui
# Installs server without prompts
# Your CI/CD handles IDE config separately
```

---

### 🔗 The Integration Flow

When all three tools work together:

```
1. User: "I want to use this MCP repo"

2. mcp-server-manager:
   - Scans: "This repo looks like an MCP server"
   - Checks: "It's not in my inventory yet"

3. repo-mcp-packager:
   - Installs: Detects Python, creates venv, installs deps
   - Verifies: Server responds to test queries
   - Reports: Installation path to other tools

4. mcp-injector:
   - Configures: Adds server to Claude/Cursor/etc.
   - Validates: JSON syntax is correct
   - Confirms: User can now use server in IDE

5. mcp-server-manager:
   - Updates: Adds to inventory with "healthy" status
   - GUI: Shows server as active and configured
```

**Without integration:** User does steps 3 and 4 manually, no step 2 or 5.

---

### 💡 Philosophy: True to Itself

This tool is the **workhorse** of the suite. It follows the principle:

- **Standard location** - installs to predictable paths
- **Self-installing** - detects what's needed automatically
- **Self-cleaning** - surgical uninstall removes everything
- **Self-contained** - works alone if you need it to

When integrated, it becomes the **engine** of a fully autonomous system where:

1. Detection happens automatically (manager)
2. Installation happens automatically (packager)
3. Configuration happens automatically (injector)
4. Validation happens automatically (manager)

**The packager is the "builder"**

- Standalone = you tell it what to build and where
- Integrated = the system orchestrates what to build, packager executes

You choose the level of automation you need.

---

### 🎭 Role in the Suite

Think of the three tools as a team:

- **mcp-server-manager**: The scout—discovers opportunities
- **repo-mcp-packager**: The builder—makes things work
- **mcp-injector**: The connector—hooks everything together

Standalone packager = you're the scout and connector
Integrated packager = it focuses on what it does best (building)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## 📝 License

This project is open-source. See LICENSE for details.

---

## 🏁 Status
**Production-ready** for agent-driven replication.
