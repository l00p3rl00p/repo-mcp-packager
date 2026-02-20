import argparse
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = REPO_ROOT / "serverinstaller" / "install.py"

spec = importlib.util.spec_from_file_location("packager_install", INSTALL_PATH)
packager_install = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(packager_install)
NexusInstaller = packager_install.NexusInstaller
get_global_ide_paths = packager_install.get_global_ide_paths


def make_args():
    return argparse.Namespace(
        headless=True,
        machine=False,
        npm_policy="global",
    )


class PackagerResilienceTests(unittest.TestCase):
    def test_preflight_permission_failure_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            args = make_args()
            installer = NexusInstaller(args)
            installer.project_root = Path(temp_dir)
            os.chmod(temp_dir, stat.S_IREAD | stat.S_IEXEC)
            try:
                with self.assertRaises(SystemExit):
                    installer.pre_flight_checks()
            finally:
                os.chmod(temp_dir, stat.S_IRWXU)

    def test_setup_npm_reports_missing_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            args = make_args()
            installer = NexusInstaller(args)
            installer.project_root = Path(temp_dir)
            gui_dir = installer.project_root / "gui"
            gui_dir.mkdir(parents=True, exist_ok=True)
            (gui_dir / "package.json").write_text('{"name":"x","version":"1.0.0"}', encoding="utf-8")
            with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaises(SystemExit):
                    installer.setup_npm({"gui_project": True})

    def test_malformed_global_config_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_home:
            cfg = Path(temp_home) / ".mcp-tools" / "config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text("{ bad-json", encoding="utf-8")
            with mock.patch("pathlib.Path.home", return_value=Path(temp_home)):
                data = get_global_ide_paths()
            self.assertEqual(data, {})
            backups = list((Path(temp_home) / ".mcp-tools").glob("config.json.corrupt.*"))
            self.assertTrue(backups)


if __name__ == "__main__":
    unittest.main()
