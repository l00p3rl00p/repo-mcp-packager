# Environment - Shesha Clean Room Installer

Technical environment requirements and audit logic.

---

## 🔍 Core Dependency Rules

### 1. Python Compatibility
* **Installer**: Python 3.9+ (hardened for legacy environments).
* **Application**: Typically Python 3.11+.

### 2. Node.js & NPM
* Only required for GUI components. Supports selective isolation.

### 3. Docker
* Required for sandbox features and query tracing.

---

## 🛠 Environment Audit Logic

The installer performs a non-destructive audit including Binary discovery (`pip`, `npm`, `docker`) and Component inventory scanning.

---

## ⚙️ Configuration Policies

### NPM Isolation
* `local`: Isolated binaries (recommended).
* `global`: Host system `npm`.

### Docker Enforcement
* `fail`: Abort if missing.
* `skip`: Proceed without sandbox features.
