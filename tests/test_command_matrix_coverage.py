import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_MD = REPO_ROOT / "COMMANDS.md"
WIDGETS_JSON = REPO_ROOT / "gui" / "widgets.json"


class CommandMatrixCoverageTests(unittest.TestCase):
    def test_every_documented_command_has_widget(self):
        import json

        rows = []
        for line in COMMANDS_MD.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("| **"):
                rows.append([part.strip() for part in line.strip("|").split("|")])

        expected = 0
        for row in rows:
            global_cmd = row[1]
            direct_cmd = row[2]
            if global_cmd != "N/A":
                expected += 1
            if direct_cmd != "N/A":
                expected += 1

        widgets = json.loads(WIDGETS_JSON.read_text(encoding="utf-8"))["widgets"]
        self.assertEqual(len(widgets), expected)


if __name__ == "__main__":
    unittest.main()
