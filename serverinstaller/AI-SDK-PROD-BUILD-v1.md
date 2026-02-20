# AI-SDK-PROD-BUILD-v1: ServerInstaller — Portable Headless Install Contract

## L1 — User Outcome (Runtime Promise)

As a user/agent, I can copy the `serverinstaller/` folder into an arbitrary repo and run a **headless** install that:
- Creates an isolated venv,
- Installs required components deterministically,
- Never blocks on interactive prompts,
- Produces a verifiable before/after report,
- Can be surgically uninstalled without collateral damage.

## Quadrants (Q1–Q4)

| Q | Requirement | Pass Condition | Evidence Location |
|---|---|---|---|
| Q1 | Front Door | `install.py --help` shows headless mode + clear commands | `EVIDENCE.md` (append) |
| Q2 | Doctor + Evidence | A doctor command proves headless install/uninstall works | `EVIDENCE.md` (append) |
| Q3 | Architecture | Behavior + env vars documented; no hidden side effects | `USER_OUTCOMES.md`, `README.md` |
| Q4 | Sealed Core | No uncontrolled writes; uninstall removes only what it created | `EVIDENCE.md` (append) |

## Build Matrix (Implementation Contract)

| Item | Scope | Requirement |
|---|---|---|
| Venv re-exec | Runtime | Headless install re-execs into venv automatically if needed |
| Portability | Runtime | No reliance on sibling repos or workspace layout |
| Rollback | Runtime | Partial failure triggers cleanup and leaves host clean |
| Uninstall | Runtime | Removes the PATH markers it created and nothing else |

## Doctor (Must Run)

Run from project root:
- `python3 -m unittest /Users/almowplay/Developer/Github/mcp-creater-manager/repo-mcp-packager/tests/test_cli_smoke.py`
- `python3 -m unittest /Users/almowplay/Developer/Github/mcp-creater-manager/repo-mcp-packager/tests/test_resilience.py`

## Q2 Evidence (Canonical Location)

Append results to:
- `/Users/almowplay/Developer/Github/mcp-creater-manager/EVIDENCE.md`

Minimum evidence payload:
- A headless install run (command + exit code + key stdout lines).
- A surgical uninstall run (command + exit code + proof PATH marker removed).
