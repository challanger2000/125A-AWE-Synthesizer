import importlib.util
import sys
from pathlib import Path
import unittest
path=Path(__file__).resolve().parents[1]/"tools"/"p68_stage_win95_autostart.py"
sys.path.insert(0,str(path.parent))
spec=importlib.util.spec_from_file_location("p68",path)
p68=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p68)
class StartupIni(unittest.TestCase):
    def test_empty_run_in_windows(self):
        original=b"[windows]\r\nload=\r\nrun=\r\n[desktop]\r\npattern=0\r\n"
        out=p68.patch_win_ini(original)
        self.assertIn(b"run=C:\\AWE32\\P68BOOT.EXE\r\n",out)
        self.assertIn(b"[desktop]\r\npattern=0",out)
    def test_existing_run_preserved(self):
        x=b"[windows]\nrun=C:\\EXTRA\\OLD.EXE\n[fonts]\n"
        out=p68.patch_win_ini(x)
        self.assertIn(b"run=C:\\EXTRA\\OLD.EXE C:\\AWE32\\P68BOOT.EXE",out)
    def test_idempotent(self):
        x=b"[windows]\r\nrun=\r\n"
        self.assertEqual(p68.patch_win_ini(p68.patch_win_ini(x)),p68.patch_win_ini(x))
    def test_bad_image_refused(self):
        with self.assertRaises(ValueError):
            p68.patch_win_ini(b"[desktop]\nrun=\n")
if __name__=="__main__":
    unittest.main()
