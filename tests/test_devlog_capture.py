import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestDevlogCapture(unittest.TestCase):
    def test_run_capture_writes_subprocess_output(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        with TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            os.environ["HOME"] = tmp
            try:
                from nexus_devlog import devlog_path, run_capture, prune_devlogs

                prune_devlogs(days=90)
                devlog = devlog_path()
                run_capture(["python3", "-c", "print('hello')"], devlog=devlog, check=True)

                lines = devlog.read_text(encoding="utf-8").splitlines()
                events = [json.loads(l).get("event") for l in lines if l.strip()]
                self.assertIn("subprocess_start", events)
                self.assertIn("subprocess_end", events)
            finally:
                # restore HOME best-effort
                os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
