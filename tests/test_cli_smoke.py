import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "bootstrap.py"
INSTALLER = REPO_ROOT / "serverinstaller" / "install.py"


def run_cmd(*args, cwd=None, input_text=None):
    return subprocess.run(
        ["python3"] + [str(arg) for arg in args],
        cwd=cwd or REPO_ROOT,
        input=input_text,
        text=True,
        capture_output=True,
    )


class PackagerSmokeTests(unittest.TestCase):
    def test_bootstrap_help(self):
        result = run_cmd(BOOTSTRAP, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--update", result.stdout)

    def test_serverinstaller_help(self):
        result = run_cmd(INSTALLER, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--headless", result.stdout)

    def test_serverinstaller_headless_on_empty_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            copied = temp / "serverinstaller"
            copied.mkdir(parents=True, exist_ok=True)
            for file in (REPO_ROOT / "serverinstaller").glob("*.py"):
                copied.joinpath(file.name).write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
            result = run_cmd(copied / "install.py", "--headless", "--no-gui", "--docker-policy", "skip", cwd=temp)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
