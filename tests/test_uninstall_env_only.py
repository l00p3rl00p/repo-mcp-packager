import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
UNINSTALL = REPO_ROOT / "serverinstaller" / "uninstall.py"


def run_cmd(*args, env=None):
    return subprocess.run(
        ["python3", str(UNINSTALL), *args],
        text=True,
        capture_output=True,
        env=env,
    )


class TestEnvOnlyUninstall(unittest.TestCase):
    def test_purge_env_removes_only_envs(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)

            nexus = home / ".mcp-tools"
            (nexus / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (nexus / "bin").mkdir(parents=True, exist_ok=True)
            (nexus / "bin" / "mcp-surgeon").write_text("x", encoding="utf-8")

            srv = nexus / "servers" / "alpha"
            (srv / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (srv / "mcp_server.py").write_text("print('x')\n", encoding="utf-8")

            res = run_cmd("--purge-env", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            self.assertFalse((nexus / ".venv").exists())
            self.assertFalse((srv / ".venv").exists())
            # suite binaries + server code remains
            self.assertTrue((nexus / "bin" / "mcp-surgeon").exists())
            self.assertTrue((srv / "mcp_server.py").exists())


if __name__ == "__main__":
    unittest.main()

