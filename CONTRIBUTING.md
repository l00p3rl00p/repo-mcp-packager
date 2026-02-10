# Contributing Guide

Welcome! We appreciate your interest in improving the Git Repo MCP Converter & Installer.

---

## 📋 Table of Contents

1. [Our Philosophy](#-our-philosophy)
2. [The Golden Rule](#-the-golden-rule)
3. [Ways to Contribute](#-ways-to-contribute)
4. [Getting Started](#-getting-started)
5. [Review Process](#-review-process)

---

## 🔍 Our Philosophy

We believe in radical improvement. We will accept **any edit that makes the project better**. Whether it's a bug fix, a new feature, a documentation update, or a performance improvement—if it adds value, we want it.

---

## 🔱 The Golden Rule: Maintain Package Linkage

This repository is part of a 3-repository suite that forms the **Git-Packager** workspace:

1. **mcp-injector**
2. **mcp-server-manager**
3. **repo-mcp-packager** (this tool)

> **CRITICAL**: You must ensure that your changes **do not break the link** between these three repositories. They are tightly integrated and depend on each other to function correctly as a whole.

* **Do** improve individual components and logic.
* **Do not** break the interoperability or the bootstrap/integration patterns between them.

If your change affects the integration, please ensure you have tested it across all three repositories.

---

## 🌟 Ways to Contribute

* **Report Bugs**: Open an issue if the installer fails on a specific OS or shell.
* **Suggest Features**: We're looking for better component detection and bridging features.
* **Submit PRs**: Direct improvements to the installer logic or bridge generator.
* **Documentation**: Help us refine the Architecture and Environment guides.

---

## ⚡ Getting Started

### Development Environment
1. Clone the repository.
2. Run `python serverinstaller/audit.py` to check your current environment capabilities.
3. Test installation with `python serverinstaller/install.py --headless`.

### Project Structure
* `serverinstaller/`: Core installer logic and scripts.
* `bridge.py`: MCP bridge generator.
* `bootstrap.py`: Workspace-wide bootstrapper.

---

## 📝 Review Process

1. **Check for "Bloat"**: Does your change add unnecessary global dependencies?
2. **Validate Headless**: Does this break the `--headless` automation outcome?
3. **Cross-Repo Test**: Does `python bootstrap.py` still work for all three repos?

Once verified, we aim for a quick review and merge.
