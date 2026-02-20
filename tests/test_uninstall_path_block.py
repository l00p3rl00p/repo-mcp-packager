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


class TestUninstallPathBlock(unittest.TestCase):
    def test_removes_path_block_from_zshrc(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            zshrc = home / ".zshrc"
            zshrc.write_text(
                "\n".join(
                    [
                        "export FOO=bar",
                        "# Workforce Nexus Block START",
                        'export PATH="~/.mcp-tools/bin:$PATH"',
                        "# Workforce Nexus Block END",
                        "export BAR=baz",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            # create central targets so uninstall has something to do
            (home / ".mcp-tools").mkdir(parents=True, exist_ok=True)
            (home / ".mcpinv" / "logs").mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["SHELL"] = "/bin/zsh"

            res = run_cmd("--purge-data", "--remove-path-block", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            content = zshrc.read_text(encoding="utf-8")
            self.assertIn("export FOO=bar", content)
            self.assertIn("export BAR=baz", content)
            self.assertNotIn("Workforce Nexus Block START", content)
            self.assertNotIn("Workforce Nexus Block END", content)

            backups = list(home.glob(".zshrc.backup.*"))
            self.assertTrue(backups)

    def test_removes_path_block_from_bashrc(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            bashrc = home / ".bashrc"
            bashrc.write_text(
                "\n".join(
                    [
                        "alias ll='ls -la'",
                        "# Workforce Nexus Block START",
                        'export PATH="~/.mcp-tools/bin:$PATH"',
                        "# Workforce Nexus Block END",
                        "alias gs='git status'",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            (home / ".mcp-tools").mkdir(parents=True, exist_ok=True)
            (home / ".mcpinv" / "logs").mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["SHELL"] = "/bin/bash"

            res = run_cmd("--purge-data", "--remove-path-block", "--yes", env=env)
            self.assertEqual(res.returncode, 0, res.stderr + "\n" + res.stdout)

            content = bashrc.read_text(encoding="utf-8")
            self.assertIn("alias ll=", content)
            self.assertIn("alias gs=", content)
            self.assertNotIn("Workforce Nexus Block START", content)
            self.assertNotIn("Workforce Nexus Block END", content)


if __name__ == "__main__":
    unittest.main()
