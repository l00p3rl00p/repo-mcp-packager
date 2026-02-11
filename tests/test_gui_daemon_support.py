import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUI_SERVER = REPO_ROOT / "gui" / "server.py"


def load_gui_server_module():
    spec = importlib.util.spec_from_file_location("nexus_gui_server", GUI_SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GuiDaemonSupportTests(unittest.TestCase):
    def test_expand_user_paths_expands_tilde(self):
        mod = load_gui_server_module()
        expanded = mod._expand_user_paths(["~/test-path", "plain"])
        self.assertTrue(expanded[0].startswith(str(Path.home())), expanded[0])
        self.assertEqual(expanded[1], "plain")

    def test_safe_tail_log_blocks_outside_dir(self):
        mod = load_gui_server_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed = Path(temp_dir) / "allowed"
            allowed.mkdir(parents=True, exist_ok=True)
            mod.DAEMON_LOG_DIR = allowed
            outside = Path(temp_dir) / "outside.log"
            outside.write_text("hello", encoding="utf-8")
            text = mod._safe_tail_log(outside)
            self.assertIn("Invalid log path", text)

    def test_safe_tail_log_reads_tail(self):
        mod = load_gui_server_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed = Path(temp_dir) / "allowed"
            allowed.mkdir(parents=True, exist_ok=True)
            mod.DAEMON_LOG_DIR = allowed
            mod.MAX_LOG_BYTES = 16
            log = allowed / "x.log"
            log.write_text("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", encoding="utf-8")
            text = mod._safe_tail_log(log)
            self.assertTrue(text.endswith("QRSTUVWXYZ"), text)


if __name__ == "__main__":
    unittest.main()

