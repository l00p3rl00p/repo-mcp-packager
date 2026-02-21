import os
import subprocess
import sys
import time
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


class TestFullWipeTerminatesProcesses(unittest.TestCase):
    def test_full_wipe_terminates_background_process(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "Desktop").mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["HOME"] = str(home)

            # Spawn a background python process whose cmdline includes "nexus_tray.py"
            # so the uninstaller's conservative matcher will target it.
            proc = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(300)", "nexus_tray.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            try:
                time.sleep(0.2)
                self.assertIsNone(proc.poll())

                # Simulate real launcher behavior: write pidfile for uninstall to consume.
                (home / ".mcpinv").mkdir(parents=True, exist_ok=True)
                (home / ".mcpinv" / "nexus.pid").write_text(str(proc.pid) + "\n", encoding="utf-8")

                # Create central targets so uninstall has something to do.
                nexus = home / ".mcp-tools"
                (nexus / ".venv").mkdir(parents=True, exist_ok=True)
                (home / ".mcpinv").mkdir(parents=True, exist_ok=True)

                res = run_cmd("--purge-data", "--kill-venv", "--yes", env=env)
                self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

                # Process should be terminated during full wipe.
                for _ in range(30):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(proc.poll())
            finally:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
