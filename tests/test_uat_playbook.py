import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib import request


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
PACKAGER_BOOTSTRAP = REPO_ROOT / "bootstrap.py"
PACKAGER_INSTALL = REPO_ROOT / "serverinstaller" / "install.py"
PACKAGER_UNINSTALL = REPO_ROOT / "serverinstaller" / "uninstall.py"
GUI_SERVER = REPO_ROOT / "gui" / "server.py"
INJECTOR = WORKSPACE_ROOT / "mcp-injector" / "mcp_injector.py"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http_get_json(url: str):
    with request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class UatPlaybookTests(unittest.TestCase):
    def test_user_uat_playbook_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env = dict(os.environ)
            env["HOME"] = str(temp / "home")
            Path(env["HOME"]).mkdir(parents=True, exist_ok=True)

            # 1) "Read the readme"
            readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
            self.assertIn("install", readme.lower())

            # 2) "Install 2 components of the server"
            install_packager = subprocess.run(
                ["python3", str(PACKAGER_INSTALL), "--headless", "--no-gui", "--docker-policy", "skip"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(install_packager.returncode, 0, install_packager.stderr)

            install_observer = subprocess.run(
                ["python3", "bootstrap.py", "--lite"],
                cwd=WORKSPACE_ROOT / "mcp-server-manager",
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(install_observer.returncode, 0, install_observer.stderr)

            # 3) "Run/access GUI" + 4) "Try a GUI command"
            port = free_port()
            gui_proc = subprocess.Popen(
                ["python3", str(GUI_SERVER), "--port", str(port)],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            try:
                started = False
                for _ in range(30):
                    time.sleep(0.2)
                    try:
                        widgets = http_get_json(f"http://127.0.0.1:{port}/api/widgets")
                        started = True
                        break
                    except Exception:
                        continue
                self.assertTrue(started, "GUI server did not start")
                self.assertIn("widgets", widgets)

                run_result = http_post_json(
                    f"http://127.0.0.1:{port}/api/run",
                    {"widget_id": "surgeon_list_clients_direct", "args": ""},
                )
                self.assertTrue(run_result["ok"], run_result.get("stderr", ""))

                logs = http_get_json(f"http://127.0.0.1:{port}/api/logs")
                self.assertTrue(len(logs.get("logs", [])) > 0)
            finally:
                gui_proc.terminate()
                gui_proc.wait(timeout=10)
                if gui_proc.stdout:
                    gui_proc.stdout.close()
                if gui_proc.stderr:
                    gui_proc.stderr.close()

            # 5) "See if I can see it in Claude MCP"
            claude_cfg = temp / "claude_desktop_config.json"
            add_claude = subprocess.run(
                ["python3", str(INJECTOR), "--config", str(claude_cfg), "--add"],
                input="4\nuat-dummy\npython3\n-c,print('pong')\nn\n\n",
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(add_claude.returncode, 0, add_claude.stderr)
            payload = json.loads(claude_cfg.read_text(encoding="utf-8"))
            self.assertIn("uat-dummy", payload.get("mcpServers", {}))

            # 6) "Shutdown" (already done via GUI terminate)

            # 7) "Uninstall 1 component"
            uninstall = subprocess.run(
                ["python3", str(PACKAGER_UNINSTALL)],
                cwd=REPO_ROOT,
                input="n\n",
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(uninstall.returncode, 0, uninstall.stderr)

            # 8) "Install application again"
            reinstall = subprocess.run(
                ["python3", str(PACKAGER_INSTALL), "--headless", "--no-gui", "--docker-policy", "skip"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(reinstall.returncode, 0, reinstall.stderr)

            # 9/10/11) "GUI responds + Claude + other IDE responds"
            codex_cfg = temp / "codex_mcp_servers.json"
            aistudio_cfg = temp / "aistudio_mcp_servers.json"
            for cfg in [codex_cfg, aistudio_cfg]:
                add = subprocess.run(
                    ["python3", str(INJECTOR), "--config", str(cfg), "--add"],
                    input="4\nuat-dummy\npython3\n-c,print('pong')\nn\n\n",
                    text=True,
                    capture_output=True,
                    env=env,
                )
                self.assertEqual(add.returncode, 0, add.stderr)
                data = json.loads(cfg.read_text(encoding="utf-8"))
                self.assertIn("uat-dummy", data.get("mcpServers", {}))

            # 12) "test retrieving from all"
            for cfg in [claude_cfg, codex_cfg, aistudio_cfg]:
                listed = subprocess.run(
                    ["python3", str(INJECTOR), "--config", str(cfg), "--list"],
                    text=True,
                    capture_output=True,
                    env=env,
                )
                self.assertEqual(listed.returncode, 0, listed.stderr)
                self.assertIn("uat-dummy", listed.stdout)


if __name__ == "__main__":
    unittest.main()
