import os
import json
import unittest
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = REPO_ROOT / "bootstrap.py"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("nexus_bootstrap", BOOTSTRAP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestInstallState(unittest.TestCase):
    def setUp(self):
        self._old_home = os.environ.get("HOME")
        self._tmp = TemporaryDirectory()
        os.environ["HOME"] = self._tmp.name

    def tearDown(self):
        if self._old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._old_home
        self._tmp.cleanup()

    def test_detect_existing_install_false_when_empty(self):
        bootstrap = load_bootstrap()

        central = Path(self._tmp.name) / ".mcp-tools"
        self.assertFalse(bootstrap.detect_existing_install(central))

    def test_detect_existing_install_true_with_marker_dir(self):
        bootstrap = load_bootstrap()

        central = Path(self._tmp.name) / ".mcp-tools"
        (central / "repo-mcp-packager").mkdir(parents=True, exist_ok=True)
        self.assertTrue(bootstrap.detect_existing_install(central))

    def test_save_and_load_install_state_roundtrip(self):
        bootstrap = load_bootstrap()

        central = Path(self._tmp.name) / ".mcp-tools"
        central.mkdir(parents=True, exist_ok=True)
        bootstrap.save_install_state(central, installed=True, tier="industrial", last_action="install_full")

        state = bootstrap.load_install_state(central)
        self.assertTrue(state.get("installed"))
        self.assertEqual(state.get("tier"), "industrial")
        self.assertEqual(state.get("last_action"), "install_full")
        self.assertIsInstance(state.get("last_updated_utc"), str)

    def test_load_install_state_tolerates_malformed_json(self):
        bootstrap = load_bootstrap()

        central = Path(self._tmp.name) / ".mcp-tools"
        central.mkdir(parents=True, exist_ok=True)
        (central / bootstrap.STATE_FILENAME).write_text("{not-json", encoding="utf-8")

        state = bootstrap.load_install_state(central)
        self.assertTrue(state.get("installed"))

    def test_load_install_state_tolerates_non_dict_json(self):
        bootstrap = load_bootstrap()

        central = Path(self._tmp.name) / ".mcp-tools"
        central.mkdir(parents=True, exist_ok=True)
        (central / bootstrap.STATE_FILENAME).write_text(json.dumps(["x"]), encoding="utf-8")

        state = bootstrap.load_install_state(central)
        self.assertTrue(state.get("installed"))


if __name__ == "__main__":
    unittest.main()
