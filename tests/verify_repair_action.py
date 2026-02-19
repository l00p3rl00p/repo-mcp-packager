
import unittest
import sys
import shutil
from pathlib import Path

# Adjust path to find mcp_injector from ../mcp-injector/mcp_injector.py
# Assuming this script is run from repo-mcp-packager/ or similar
repo_root = Path(__file__).resolve().parent
injector_path = repo_root / "mcp-injector" / "mcp_injector.py"

if not injector_path.exists():
    # Fallback for when running in mcp-creater-manager root
    injector_path = repo_root / "mcp-injector" / "mcp_injector.py"

# But we are testing bootstrap.py repair flag.
# Let's import bootstrap
sys.path.append(str(repo_root / "repo-mcp-packager"))
try:
    import bootstrap
except ImportError:
    # Try importing from current dir if running inside repo-mcp-packager
    sys.path.append(str(repo_root))
    import bootstrap

class TestRepairAction(unittest.TestCase):
    def setUp(self):
        self.central = Path.home() / ".mcp-tools"
        self.venv = self.central / ".venv"
        self.bin = self.central / "bin"
        
    def test_repair_restores_venv(self):
        """Test that --repair restores a missing venv."""
        print("\n🧪 Testing Repair: Corrupting Venv...")
        
        # 1. Corrupt venv (rename it)
        if self.venv.exists():
            shutil.rmtree(self.venv)
            
        self.assertFalse(self.venv.exists(), "Venv still exists after deletion")
        
        # 2. Run Repair
        print("🔧 Running Repair...")
        try:
            bootstrap.setup_nexus_venv(self.central)
            # We are calling the function directly to test the logic, 
            # effectively simulating what --repair does.
            # Ideally we would subprocess call bootstrap.py --repair
        except Exception as e:
            self.fail(f"Repair failed: {e}")
            
        # 3. Verify Restoration
        self.assertTrue(self.venv.exists(), "Venv was NOT restored by repair")
        self.assertTrue((self.venv / "bin" / "python").exists() or (self.venv / "Scripts" / "python.exe").exists(), "Python binary missing in restored venv")
        print("✅ Repair successful: Venv restored.")

    def test_repair_restores_entry_points(self):
        """Test that --repair restores missing entry points."""
        print("\n🧪 Testing Repair: Deleting Entry Points...")
        
        # 1. Delete an entry point
        activator = self.bin / "mcp-activator"
        if activator.exists():
            activator.unlink()
            
        self.assertFalse(activator.exists(), "mcp-activator still exists after deletion")
        
        # 2. Run Repair
        print("🔧 Running Repair...")
        bootstrap.create_hardened_entry_points(self.central)
        
        # 3. Verify
        self.assertTrue(activator.exists(), "mcp-activator was NOT restored")
        print("✅ Repair successful: Entry points restored.")

if __name__ == '__main__':
    unittest.main()
