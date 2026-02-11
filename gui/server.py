#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import json
import shlex
import subprocess
import time
import datetime
import os
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional


GUI_DIR = Path(__file__).resolve().parent
REPO_ROOT = GUI_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
WIDGETS_FILE = GUI_DIR / "widgets.json"
LOG_FILE = GUI_DIR / "actions.log"
DAEMON_LOG_DIR = GUI_DIR / "daemon-logs"
DEFAULT_REGISTRY_FILE = GUI_DIR / "daemon-registry.json"

RUNNING_DAEMONS: dict[int, dict] = {}
MAX_RUNNING_DAEMONS = 5
MAX_LOG_BYTES = 64 * 1024

def _expand_user_paths(args: List[str]) -> List[str]:
    out: List[str] = []
    for arg in args:
        if isinstance(arg, str) and arg.startswith("~"):
            out.append(str(Path(arg).expanduser()))
        else:
            out.append(arg)
    return out


def _recover_json_file(path: Path, default_payload: dict, label: str) -> dict:
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_suffix(f"{path.suffix}.corrupt.{stamp}")
    try:
        if path.exists():
            path.replace(backup)
    except Exception:
        pass
    path.write_text(json.dumps(default_payload, indent=2), encoding="utf-8")
    # Keep this silent by default (production GUI should not spam stdout).
    # If you need visibility, tail `actions.log` or enable debug logging in the server process.
    return default_payload


def load_widgets() -> dict:
    default_payload = {"tiers": ["lite", "standard", "permanent"], "widgets": []}
    try:
        data = json.loads(WIDGETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = _recover_json_file(WIDGETS_FILE, default_payload, "widgets.json")
    if not isinstance(data, dict):
        data = _recover_json_file(WIDGETS_FILE, default_payload, "widgets.json")
    widgets = data.get("widgets", [])
    if not isinstance(widgets, list):
        data = _recover_json_file(WIDGETS_FILE, default_payload, "widgets.json")
        widgets = data["widgets"]
    return {
        w["id"]: w for w in widgets
        if isinstance(w, dict) and isinstance(w.get("id"), str) and isinstance(w.get("template"), str)
    }


def append_log(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")

def _central_registry_path() -> Optional[Path]:
    """
    Prefer storing daemon registry under the central install (~/.mcp-tools) so it
    survives GUI restarts regardless of current working directory.
    """
    try:
        if sys.platform == "win32":
            home = Path(os.environ["USERPROFILE"])
        else:
            home = Path.home()
        central = home / ".mcp-tools" / "repo-mcp-packager" / "gui"
        central.mkdir(parents=True, exist_ok=True)
        return central / "daemon-registry.json"
    except Exception:
        return None

def _registry_path() -> Path:
    p = _central_registry_path()
    return p if p else DEFAULT_REGISTRY_FILE

def _save_registry() -> None:
    try:
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "daemons": list(RUNNING_DAEMONS.values()),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except Exception:
        # Never block GUI on registry I/O.
        pass

def _load_registry() -> None:
    try:
        path = _registry_path()
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        daemons = raw.get("daemons") if isinstance(raw, dict) else None
        if not isinstance(daemons, list):
            return
        for d in daemons:
            if not isinstance(d, dict):
                continue
            pid = d.get("pid")
            if not isinstance(pid, int) or pid <= 0:
                continue
            RUNNING_DAEMONS[pid] = d
    except Exception:
        return

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        # If we can't determine, treat as alive to avoid accidental cleanup.
        return True

def _reap_dead_daemons() -> None:
    dead = [pid for pid in RUNNING_DAEMONS.keys() if not _pid_alive(pid)]
    for pid in dead:
        RUNNING_DAEMONS.pop(pid, None)
    if dead:
        _save_registry()

def _safe_tail_log(path: Path) -> str:
    try:
        resolved = path.resolve()
        allowed_root = DAEMON_LOG_DIR.resolve()
        if not (resolved == allowed_root or allowed_root in resolved.parents):
            return "Invalid log path."
        if not resolved.exists() or not resolved.is_file():
            return "Log file not found."
        size = resolved.stat().st_size
        with resolved.open("rb") as handle:
            if size > MAX_LOG_BYTES:
                handle.seek(-MAX_LOG_BYTES, os.SEEK_END)
            raw = handle.read(MAX_LOG_BYTES)
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode(errors="replace")
    except Exception as exc:
        return f"Failed to read log: {exc}"

class GuiHandler(http.server.SimpleHTTPRequestHandler):
    widgets = load_widgets()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(GUI_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/widgets":
            payload = {"widgets": list(self.widgets.values())}
            return self._send_json(200, payload)
        if path == "/api/daemons":
            _reap_dead_daemons()
            return self._send_json(200, {"daemons": list(RUNNING_DAEMONS.values())})
        if path == "/api/daemon-log":
            _reap_dead_daemons()
            query = urlparse(self.path).query
            params = {}
            for part in query.split("&"):
                if not part:
                    continue
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v
            try:
                pid = int(params.get("pid", "0"))
            except Exception:
                pid = 0
            info = RUNNING_DAEMONS.get(pid)
            if not info:
                return self._send_json(404, {"error": "Unknown pid"})
            text = _safe_tail_log(Path(info["log_file"]))
            return self._send_json(200, {"pid": pid, "log": text})
        if path == "/api/logs":
            if not LOG_FILE.exists():
                return self._send_json(200, {"logs": []})
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-120:]
            logs = []
            for line in lines:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    logs.append({"timestamp": "", "message": line, "ok": False})
            return self._send_json(200, {"logs": logs})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/run":
            return self._run_widget_command()
        if path == "/api/stop":
            return self._stop_daemon()
        return self._send_json(404, {"error": "Not Found"})

    def _run_widget_command(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return self._send_json(400, {"error": "Missing request body"})

        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "Invalid JSON"})

        widget_id = body.get("widget_id", "").strip()
        arg_string = body.get("args", "").strip()
        if widget_id not in self.widgets:
            return self._send_json(404, {"error": "Unknown widget"})

        widget = self.widgets[widget_id]
        user_args = shlex.split(arg_string) if arg_string else []
        required = int(widget.get("args_required", 0))
        if len(user_args) < required:
            hint = widget.get("args_hint", "")
            return self._send_json(400, {"error": f"Need at least {required} args", "args_hint": hint})

        command_parts = shlex.split(widget["template"]) + user_args
        command_parts = _expand_user_paths(command_parts)
        raw_cwd = widget.get("cwd", ".")
        cmd_cwd = (REPO_ROOT / raw_cwd).resolve()
        if not cmd_cwd.exists():
            fallback = (WORKSPACE_ROOT / raw_cwd).resolve()
            if fallback.exists():
                cmd_cwd = fallback

        allowed_roots = (REPO_ROOT, WORKSPACE_ROOT)
        if not any(root == cmd_cwd or root in cmd_cwd.parents for root in allowed_roots):
            return self._send_json(400, {"error": "Invalid working directory"})

        daemon_mode = bool(widget.get("daemon", False))
        started = time.time()
        try:
            if daemon_mode:
                if len(RUNNING_DAEMONS) >= MAX_RUNNING_DAEMONS:
                    return self._send_json(429, {"error": f"Too many daemons running (max {MAX_RUNNING_DAEMONS}). Stop one first."})

                DAEMON_LOG_DIR.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d%H%M%S")
                log_path = DAEMON_LOG_DIR / f"{widget_id}.{stamp}.log"
                handle = log_path.open("w", encoding="utf-8")
                proc = subprocess.Popen(
                    command_parts,
                    cwd=cmd_cwd,
                    text=True,
                    stdout=handle,
                    stderr=handle,
                    start_new_session=True,
                )
                try:
                    handle.close()
                except Exception:
                    pass
                info = {
                    "pid": proc.pid,
                    "widget_id": widget_id,
                    "command": " ".join(command_parts),
                    "cwd": str(cmd_cwd),
                    "log_file": str(log_path),
                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                RUNNING_DAEMONS[proc.pid] = info
                _save_registry()
                result = {
                    "ok": True,
                    "exit_code": None,
                    "command": info["command"],
                    "cwd": info["cwd"],
                    "stdout": f"Started daemon pid={proc.pid}\nLog: {log_path}\n\nTo stop: kill {proc.pid} (or POST /api/stop with pid).",
                    "stderr": "",
                    "duration_sec": round(time.time() - started, 2),
                    "widget_id": widget_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "daemon": info,
                }
            else:
                proc = subprocess.run(
                    command_parts,
                    cwd=cmd_cwd,
                    text=True,
                    capture_output=True,
                    timeout=120
                )
                ok = proc.returncode == 0
                result = {
                    "ok": ok,
                    "exit_code": proc.returncode,
                    "command": " ".join(command_parts),
                    "cwd": str(cmd_cwd),
                    "stdout": proc.stdout[-10000:],
                    "stderr": proc.stderr[-10000:],
                    "duration_sec": round(time.time() - started, 2),
                    "widget_id": widget_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
            append_log(result)
            return self._send_json(200, result)
        except subprocess.TimeoutExpired as exc:
            result = {
                "ok": False,
                "exit_code": -1,
                "command": " ".join(command_parts),
                "cwd": str(cmd_cwd),
                "stdout": (exc.stdout or "")[-10000:],
                "stderr": ((exc.stderr or "") + "\nTimed out after 120s")[-10000:],
                "duration_sec": round(time.time() - started, 2),
                "widget_id": widget_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            append_log(result)
            return self._send_json(200, result)
        except Exception as exc:
            result = {
                "ok": False,
                "exit_code": -2,
                "command": " ".join(command_parts),
                "cwd": str(cmd_cwd),
                "stdout": "",
                "stderr": f"Execution error: {exc}",
                "duration_sec": round(time.time() - started, 2),
                "widget_id": widget_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            append_log(result)
            return self._send_json(200, result)

    def _stop_daemon(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return self._send_json(400, {"error": "Missing request body"})
        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "Invalid JSON"})
        pid = body.get("pid")
        if not isinstance(pid, int):
            return self._send_json(400, {"error": "Expected integer pid"})
        info = RUNNING_DAEMONS.get(pid)
        if not info:
            return self._send_json(404, {"error": "Unknown pid"})

        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            RUNNING_DAEMONS.pop(pid, None)
            return self._send_json(200, {"ok": True, "message": "Process already exited"})
        except Exception as exc:
            return self._send_json(500, {"error": f"Failed to stop pid {pid}: {exc}"})

        # Best-effort wait then hard kill.
        time.sleep(0.5)
        try:
            os.killpg(pid, 0)
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            pass

        RUNNING_DAEMONS.pop(pid, None)
        _save_registry()
        append_log({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "message": f"Stopped daemon pid={pid}", "ok": True})
        return self._send_json(200, {"ok": True, "message": f"Stopped pid {pid}"})

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="Nexus GUI command server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    _load_registry()
    _reap_dead_daemons()

    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), GuiHandler) as server:
        print(f"Nexus GUI running at http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
