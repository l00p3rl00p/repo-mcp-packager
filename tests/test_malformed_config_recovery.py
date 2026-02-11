import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
GUI_SERVER_PATH = REPO_ROOT / "gui" / "server.py"
VERIFY_PATH = REPO_ROOT / "serverinstaller" / "verify.py"


gui_spec = importlib.util.spec_from_file_location("packager_gui_server", GUI_SERVER_PATH)
gui_server = importlib.util.module_from_spec(gui_spec)
assert gui_spec and gui_spec.loader
gui_spec.loader.exec_module(gui_server)

verify_spec = importlib.util.spec_from_file_location("packager_verify", VERIFY_PATH)
packager_verify = importlib.util.module_from_spec(verify_spec)
assert verify_spec and verify_spec.loader
verify_spec.loader.exec_module(packager_verify)
SheshaVerifier = packager_verify.SheshaVerifier


class PackagerMalformedConfigTests(unittest.TestCase):
    def test_gui_widgets_json_recovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            widgets = Path(temp_dir) / "widgets.json"
            widgets.write_text("{ bad-json", encoding="utf-8")
            with mock.patch.object(gui_server, "WIDGETS_FILE", widgets):
                with mock.patch("builtins.print") as p:
                    loaded = gui_server.load_widgets()
            self.assertEqual(loaded, {})
            p.assert_not_called()
            backups = list(Path(temp_dir).glob("widgets.json.corrupt.*"))
            self.assertTrue(backups)
            payload = widgets.read_text(encoding="utf-8")
            self.assertIn('"widgets"', payload)

    def test_verify_manifest_recovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            manifest = project / ".librarian" / "manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("{ bad-json", encoding="utf-8")
            verifier = SheshaVerifier(project)
            with mock.patch("builtins.print") as p:
                verifier.generate_report()
            p.assert_not_called()
            backups = list((project / ".librarian").glob("manifest.json.corrupt.*"))
            self.assertTrue(backups)
            # Recovery should leave a valid JSON file behind so this doesn't repeat.
            recovered = manifest.read_text(encoding="utf-8")
            self.assertIn('"install_artifacts"', recovered)
            self.assertIsInstance(packager_verify.json.loads(recovered), dict)


if __name__ == "__main__":
    unittest.main()
