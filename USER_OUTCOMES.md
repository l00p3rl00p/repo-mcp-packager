# User Outcomes: Clean & Portable Installer

The Compass for Shesha installation success. This document defines what success looks like in human terms and ensures that the technical path aligns with the mission of "Clean Replication."

## Mission Statement
To provide a "Just Works" installation experience that creates a zero-leak, isolated environment on any system, allowing agents to replicate the Shesha RLM stack without friction.

## Successful Outcomes

- **Portability**: The `/serverinstaller` directory can be copied to any fork/repo and execute correctly without external dependencies. The installer is a standalone wavefront. It does not carry opaque binaries; it bootstraps from the host's existing tools and the local workspace.
- **Inventory Awareness**: The installer identifies all available components (Server, GUI, Docker) and allows the user to selectively install only what they need, preventing "package bloat" on minimalist deployments.
- **Local Source Parity**: The installer installs the application *exactly as it exists* in the local root directory, respecting all custom modifications. 
- **Zero-Touch Replication**: A real agent can execute `install.py --headless` and achieve a functional stack without human intervention.
- **Surgical Integrity**: The `uninstall` command is not a hammer. It surgically reverses only the changes it made, ensuring the host system is returned to its exact pre-installation state.
- **Trust through Transparency**: The operator (human or agent) can verify every change via the "Before/After" report. No stealth modifications to the PATH or Registry.
- **Local Source Fidelity**: The installer treats the current repository state as the "source of truth." It never overwrites local experimental code with upstream templates.
- **Standalone Utilities**: The `/serverinstaller` includes portable tools like the **MCP JSON Injector**, which can be used independently to safely modify IDE config files without breaking JSON syntax.

## High-Fidelity Signals

- **Success**: `.librarian/manifest.json` correctly list all artifacts, and `verify.py` reports `[VERIFIED]` for all items.
- **Failure**: Encountering an interactive prompt in `--headless` mode. This is a critical failure of the automation outcome.
- **Success**: Running `uninstall.py` removes the `# Shesha Block` from `.zshrc` without deleting other aliases.

## Design Guardrails
- **Reject** any feature that requires global `sudo` permissions if a local `.venv` alternative exists.
- **Reject** any "auto-update" feature that replaces local configuration without a manifest-backed snapshot.
