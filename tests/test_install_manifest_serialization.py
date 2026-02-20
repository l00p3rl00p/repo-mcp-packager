import importlib.util
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = REPO_ROOT / "serverinstaller" / "install.py"


install_spec = importlib.util.spec_from_file_location("packager_install", INSTALL_PATH)
packager_install = importlib.util.module_from_spec(install_spec)
assert install_spec and install_spec.loader
install_spec.loader.exec_module(packager_install)
NexusInstaller = packager_install.NexusInstaller


class PackagerManifestWriteTests(unittest.TestCase):
    def test_write_manifest_serializes_path_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "artifact.txt").write_text("x", encoding="utf-8")

            installer = NexusInstaller.__new__(NexusInstaller)
            installer.args = types.SimpleNamespace(managed=False, headless=True)
            installer.project_root = project
            installer.artifacts = [project / "artifact.txt"]
            installer.log = lambda *_args, **_kwargs: None

            installer.write_manifest({"timestamp": "2026-02-11T00:00:00"})
            manifest_path = project / ".librarian" / "manifest.json"
            data = packager_install.json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertIn("install_artifacts", data)
            self.assertEqual(data["install_artifacts"], [str(project / "artifact.txt")])


if __name__ == "__main__":
    unittest.main()
