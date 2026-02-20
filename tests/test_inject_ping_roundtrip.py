import json
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
INJECTOR_SCRIPT = WORKSPACE_ROOT / "mcp-injector" / "mcp_injector.py"


class InjectPingRoundtripTests(unittest.TestCase):
    def test_inject_and_ping_dummy_server(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            config_path = temp / "claude_config.json"
            server_path = temp / "dummy_mcp_server.py"
            server_path.write_text(
                "import sys\n"
                "if '--ping' in sys.argv:\n"
                "    print('pong')\n"
                "else:\n"
                "    print('dummy')\n",
                encoding="utf-8",
            )

            add = subprocess.run(
                [
                    "python3",
                    str(INJECTOR_SCRIPT),
                    "--config",
                    str(config_path),
                    "--add",
                ],
                input="custom\nmcp-maker-dummy\npython3\n" + str(server_path) + ",--ping\nn\n\n",
                text=True,
                capture_output=True,
            )
            self.assertEqual(add.returncode, 0, add.stderr)

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            injected = payload["mcpServers"]["mcp-maker-dummy"]
            command = [injected["command"]] + injected["args"]
            ping = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(ping.returncode, 0, ping.stderr)
            self.assertIn("pong", ping.stdout)


if __name__ == "__main__":
    unittest.main()
