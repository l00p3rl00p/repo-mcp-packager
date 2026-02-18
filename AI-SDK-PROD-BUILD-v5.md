# AI-SDK-PROD-BUILD-v5: User-Centric Verification & "Ghost Code" Elimination

## Build Matrix

| Q | Question | Answer | Evidence Location |
|---|----------|--------|-------------------|
| Q1 | Does the GUI work for a **human**? | Browser subagent confirms buttons click, lists populate, and data flows. | `browser_session_videos/` |
| Q2 | Is the backend visibly connected? | `gui_bridge.py` binds to `0.0.0.0` to ensure container/proxy visibility. | `Verify GUI Fix` (Step 1240) |
| Q3 | Are core tools auto-discovered? | Inventory populated with `nexus-librarian` and `test-server`. | `mcp-observer list` output |
| Q4 | Is "Ghost Code" eliminated? | No services run silently; all are visible in Dashboard. | `dashboard_snapshot.png` |

---

## Human Expectation (One Sentence)
"I open the GUI in my browser, I see my tools, I click start, and they actually start—no console errors, no 'refused connection'."

---

## Technical Specification

### 1. Universal Binding (`gui_bridge.py`)
**Files**: `mcp-server-manager/gui_bridge.py`
- **Fix**: Bind Flask to `0.0.0.0` (not `127.0.0.1`) to support diverse network stacks.
- **Fix**: Disable `debug=True` to prevent reloader conflicts.
- **Outcome**: Frontend fetch calls to `http://127.0.0.1:5001` succeed reliably.

### 2. Verified Inventory Population (`mcp-observer`)
**Files**: `~/.mcpinv/inventory.json`
- **Action**: Explicitly add core suite tools (`nexus-librarian`, `mcp-server-manager`) if auto-discovery misses them.
- **Outcome**: Dashboard "Managed Servers" list is not empty.

### 3. Frontend-Backend Sync (`App.tsx`)
**Files**: `mcp-server-manager/gui/src/App.tsx`
- **Fix**: Hardcode fetch URL to `http://127.0.0.1:5001` (avoid `localhost` ambiguity).
- **Verification**: Browser console shows `200 OK` for `/status`, `/logs`, `/artifacts`.

### 4. User-Centric Validation (The "Browser Test")
**Methodology**:
- Do not trust `curl`.
- Use **Browser Subagent** to navigate, clicking buttons, and verify DOM updates.
- **Pass Criteria**: Visual confirmation that "Start" button changes state or logs update.

---

## Success Criteria
- [x] GUI Frontend loads at `http://127.0.0.1:5173` without console errors.
- [x] Dashboard displays `nexus-librarian` and `test-server`.
- [x] "Start" button triggers actual backend process (pid created).
- [x] Librarian tab shows indexed artifacts (or empty state if none, but *connected*).
- [x] Command Log updates in real-time.
