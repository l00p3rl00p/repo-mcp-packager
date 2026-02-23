import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_MD = REPO_ROOT / "commands.md"
WIDGETS_JSON = REPO_ROOT / "gui" / "widgets.json"


class CommandMatrixCoverageTests(unittest.TestCase):
    def test_every_documented_command_has_widget(self):
        import json

        # commands.md tables may evolve; we count the number of documented *direct commands*
        # (backticked) and require GUI widgets to cover them.
        expected_commands = []
        for line in COMMANDS_MD.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("| **"):
                continue
            # collect any backticked command snippets in the row
            parts = line.split("`")
            for i in range(1, len(parts), 2):
                cmd = parts[i].strip()
                if cmd and cmd != "N/A":
                    expected_commands.append(cmd)

        widgets = json.loads(WIDGETS_JSON.read_text(encoding="utf-8"))["widgets"]
        templates = {w.get("template") for w in widgets if isinstance(w, dict)}
        # CLI-only administrative commands are not expected to be exposed as GUI widgets.
        expected_gui_commands = [
            cmd for cmd in expected_commands
            if "uninstall.py" not in cmd and " --server" not in cmd and "nexus.sh" not in cmd and "nexus.bat" not in cmd
        ]
        missing = [cmd for cmd in expected_gui_commands if cmd not in templates]
        self.assertEqual(missing, [], f"Missing widget templates for commands: {missing}")


if __name__ == "__main__":
    unittest.main()
