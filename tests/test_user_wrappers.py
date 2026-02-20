import os
import tempfile
import unittest
from pathlib import Path


class TestUserWrappers(unittest.TestCase):
    def test_install_user_wrappers_writes_marker_scripts(self):
        # Import locally so this test doesn't hard-depend on external environment.
        from bootstrap import install_user_wrappers

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            central = tmp_path / "central"
            (central / "bin").mkdir(parents=True, exist_ok=True)

            # Create fake central bin executables
            for name in ("mcp-surgeon", "mcp-observer", "mcp-librarian", "mcp-activator"):
                p = central / "bin" / name
                p.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
                p.chmod(p.stat().st_mode | 0o111)

            wrappers_dir = tmp_path / "wrappers"
            install_user_wrappers(central=central, wrappers_dir=wrappers_dir, overwrite=False, verbose=False)

            for name in ("mcp-surgeon", "mcp-observer", "mcp-librarian", "mcp-activator"):
                wrapper = wrappers_dir / name
                self.assertTrue(wrapper.exists())
                content = wrapper.read_text(encoding="utf-8", errors="ignore")
                self.assertIn("Workforce Nexus User Wrapper", content)
                self.assertIn(str(central / "bin" / name), content)

    def test_uninstall_purge_removes_only_marked_wrappers(self):
        # Central-only purge should delete Nexus-managed wrapper files from ~/.local/bin.
        # We simulate HOME to a temp folder so we don't touch the real machine.
        # Note: repo root also has an uninstall entrypoint; the canonical implementation lives
        # in serverinstaller/uninstall.py and is not an importable package module.
        import importlib.util

        repo_root = Path(__file__).resolve().parent.parent
        uninstall_path = repo_root / "serverinstaller" / "uninstall.py"
        spec = importlib.util.spec_from_file_location("nexus_serverinstaller_uninstall", uninstall_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        NexusUninstaller = module.NexusUninstaller

        with tempfile.TemporaryDirectory() as tmp:
            tmp_home = Path(tmp)
            wrappers_dir = tmp_home / ".local" / "bin"
            wrappers_dir.mkdir(parents=True, exist_ok=True)

            managed = wrappers_dir / "mcp-activator"
            managed.write_text(
                "#!/usr/bin/env bash\n# Workforce Nexus User Wrapper (managed by repo-mcp-packager)\n",
                encoding="utf-8",
            )

            unmanaged = wrappers_dir / "mcp-surgeon"
            unmanaged.write_text("#!/usr/bin/env bash\necho not nexus\n", encoding="utf-8")

            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(tmp_home)
            try:
                u = NexusUninstaller(
                    project_root=tmp_home / "dummy-project",
                    kill_venv=True,
                    purge_data=True,
                    verbose=False,
                    devlog=None,
                    yes=True,
                    dry_run=False,
                )
                # Wrapper cleanup is opt-in.
                u.remove_wrappers = True
                rc = u.run()
                self.assertEqual(rc, 0)
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

            self.assertFalse(managed.exists())
            self.assertTrue(unmanaged.exists())
