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


class TestCentralOnlyUninstall(unittest.TestCase):
    def test_purge_data_keeps_venv_when_kill_venv_false(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)

            nexus = home / ".mcp-tools"
            venv = nexus / ".venv"
            keep_marker = venv / "KEEP"
            (venv / "bin").mkdir(parents=True, exist_ok=True)
            keep_marker.write_text("x", encoding="utf-8")
            (nexus / "repo-mcp-packager").mkdir(parents=True, exist_ok=True)
            (nexus / "trash.txt").write_text("t", encoding="utf-8")
            (home / ".mcpinv" / "logs").mkdir(parents=True, exist_ok=True)

            res = run_cmd("--purge-data", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            self.assertTrue(venv.exists())
            self.assertTrue(keep_marker.exists())
            self.assertFalse((nexus / "trash.txt").exists())
            self.assertFalse((nexus / "repo-mcp-packager").exists())
            self.assertFalse((home / ".mcpinv").exists())

    def test_purge_data_deletes_all_when_kill_venv_true(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)

            nexus = home / ".mcp-tools"
            (nexus / ".venv").mkdir(parents=True, exist_ok=True)
            (home / ".mcpinv").mkdir(parents=True, exist_ok=True)
            (home / "Desktop").mkdir(parents=True, exist_ok=True)

            res = run_cmd("--purge-data", "--kill-venv", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)
            self.assertFalse(nexus.exists())
            self.assertFalse((home / ".mcpinv").exists())
            # Full wipe leaves behind a purge checklist on Desktop.
            checklists = list((home / "Desktop").glob("Nexus Purge Checklist *.md"))
            self.assertTrue(checklists)

    def test_kill_venv_also_removes_desktop_launcher_and_stale_aliases(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["SHELL"] = "/bin/zsh"

            nexus = home / ".mcp-tools"
            (nexus / ".venv").mkdir(parents=True, exist_ok=True)
            (home / ".mcpinv").mkdir(parents=True, exist_ok=True)

            # Desktop launcher created by setup.sh
            desktop = home / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)
            launcher = desktop / "Start Nexus.command"
            launcher.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")

            # Legacy aliases (no markers) pointing at missing files should be removed.
            zshrc = home / ".zshrc"
            zshrc.write_text(
                "\n".join(
                    [
                        "export FOO=bar",
                        "alias nx='python3 /missing/nexus-verify.py'",
                        "alias nexus='/missing/nexus.sh'",
                        "export BAR=baz",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            res = run_cmd("--purge-data", "--kill-venv", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            self.assertFalse(launcher.exists())
            content = zshrc.read_text(encoding="utf-8")
            self.assertIn("export FOO=bar", content)
            self.assertIn("export BAR=baz", content)
            self.assertNotIn("alias nx=", content)
            self.assertNotIn("alias nexus=", content)

    def test_devlog_survives_purge(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)

            nexus = home / ".mcp-tools"
            nexus.mkdir(parents=True, exist_ok=True)
            (nexus / "trash.txt").write_text("t", encoding="utf-8")
            (home / ".mcpinv" / "logs").mkdir(parents=True, exist_ok=True)

            res = run_cmd("--purge-data", "--devlog", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            devlogs = home / ".mcpinv" / "devlogs"
            self.assertTrue(devlogs.exists())
            # one file per day naming
            files = list(devlogs.glob("nexus-*.jsonl"))
            self.assertTrue(files)


if __name__ == "__main__":
    unittest.main()
