import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "bootstrap.py"

spec = importlib.util.spec_from_file_location("nexus_bootstrap", BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(bootstrap)


class SuiteIndexPrereqsTests(unittest.TestCase):
    def test_creates_inventory_and_config_if_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            central = Path(temp_dir)
            bootstrap.ensure_suite_index_prereqs(central)

            inv = central / "mcp-server-manager" / "inventory.yaml"
            cfg = central / "config.json"
            self.assertTrue(inv.exists())
            self.assertTrue(cfg.exists())
            self.assertIn("servers", inv.read_text(encoding="utf-8"))
            self.assertIn("ide_config_paths", cfg.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

