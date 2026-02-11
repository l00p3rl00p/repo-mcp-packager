import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent


def run_in(repo: Path, *args: str):
    return subprocess.run(["python3", *args], cwd=repo, text=True, capture_output=True)


class CommandsFlagsExistTests(unittest.TestCase):
    def test_bootstrap_help_has_documented_flags(self):
        result = run_in(REPO_ROOT, "bootstrap.py", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--lite", "--industrial", "--permanent", "--sync", "--update", "--gui"):
            self.assertIn(flag, out)

    def test_packager_uninstall_has_documented_flags(self):
        result = run_in(REPO_ROOT, "uninstall.py", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--kill-venv", "--purge-data"):
            self.assertIn(flag, out)

    def test_injector_help_has_documented_flags(self):
        injector = WORKSPACE_ROOT / "mcp-injector" / "mcp_injector.py"
        result = subprocess.run(["python3", str(injector), "--help"], cwd=injector.parent, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--add", "--remove", "--list", "--list-clients", "--startup-detect"):
            self.assertIn(flag, out)

    def test_librarian_help_has_documented_flags(self):
        librarian = WORKSPACE_ROOT / "mcp-link-library" / "mcp.py"
        result = subprocess.run(["python3", str(librarian), "--help"], cwd=librarian.parent, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for flag in ("--add", "--index", "--search", "--index-suite", "--server"):
            self.assertIn(flag, out)

    def test_observer_help_has_documented_subcommands(self):
        result = subprocess.run(
            ["python3", "-m", "mcp_inventory.cli", "--help"],
            cwd=str(WORKSPACE_ROOT / "mcp-server-manager"),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout + result.stderr
        for sub in ("config", "list", "add", "scan", "running", "bootstrap", "health", "gui"):
            self.assertIn(sub, out)


if __name__ == "__main__":
    unittest.main()

