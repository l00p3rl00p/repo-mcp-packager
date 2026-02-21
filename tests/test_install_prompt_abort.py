import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = REPO_ROOT / "serverinstaller" / "install.py"

spec = importlib.util.spec_from_file_location("packager_install", INSTALL_PATH)
packager_install = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(packager_install)
NexusInstaller = packager_install.NexusInstaller


class TestInstallPromptAbort(unittest.TestCase):
    def test_keyboard_interrupt_exits_cleanly(self):
        # Minimal args surface required by installer.run()
        args = SimpleNamespace(
            headless=False,
            no_gui=False,
            npm_policy="auto",
            docker_policy="skip",
            storage_path=None,
            log_dir=None,
            machine=False,
            managed=False,
            update=False,
            add_venv_to_path=False,
            generate_bridge=False,
            attach_to=None,
            forge=None,
            forge_repo=None,
            name=None,
        )
        inst = NexusInstaller(args)
        discovery = {
            "python_project": True,
            "npm_project": False,
            "gui_project": False,
            "docker_project": False,
            "python_requirements": False,
            "python_setup": False,
            "simple_script": False,
            "script_path": None,
        }

        with mock.patch.object(inst, "discover_project", return_value=discovery), mock.patch(
            "sys.stdin.isatty", return_value=True
        ), mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            with self.assertRaises(SystemExit) as ctx:
                inst.run()
        self.assertEqual(ctx.exception.code, 130)


if __name__ == "__main__":
    unittest.main()
