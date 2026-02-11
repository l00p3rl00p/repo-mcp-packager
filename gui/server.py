#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import json
import shlex
import subprocess
import time
import datetime
from pathlib import Path
from urllib.parse import urlparse


GUI_DIR = Path(__file__).resolve().parent
REPO_ROOT = GUI_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
WIDGETS_FILE = GUI_DIR / "widgets.json"
LOG_FILE = GUI_DIR / "actions.log"


def _recover_json_file(path: Path, default_payload: dict, label: str) -> dict:
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_suffix(f"{path.suffix}.corrupt.{stamp}")
    try:
        if path.exists():
            path.replace(backup)
    except Exception:
        pass
    path.write_text(json.dumps(default_payload, indent=2), encoding="utf-8")
    print(f"⚠️  Recovered malformed {label}. Backup: {backup}")
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


class GuiHandler(http.server.SimpleHTTPRequestHandler):
    widgets = load_widgets()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(GUI_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/widgets":
            payload = {"widgets": list(self.widgets.values())}
            return self._send_json(200, payload)
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
        raw_cwd = widget.get("cwd", ".")
        cmd_cwd = (REPO_ROOT / raw_cwd).resolve()
        if not cmd_cwd.exists():
            fallback = (WORKSPACE_ROOT / raw_cwd).resolve()
            if fallback.exists():
                cmd_cwd = fallback

        allowed_roots = (REPO_ROOT, WORKSPACE_ROOT)
        if not any(root == cmd_cwd or root in cmd_cwd.parents for root in allowed_roots):
            return self._send_json(400, {"error": "Invalid working directory"})

        started = time.time()
        try:
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

    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), GuiHandler) as server:
        print(f"Nexus GUI running at http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
