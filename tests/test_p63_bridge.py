"""P63 host bridge protocol tests, no copyrighted binaries or sample data."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"p63_send_guest_midi.py"
spec=importlib.util.spec_from_file_location("p63",SCRIPT)
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_note_on(self):
        self.assertEqual(bridge.frame(0x90,50,100),
                         bytes((0xA5,0x5A,0x90,50,100,0x90^50^100^0x5A)))

    def test_program_and_control(self):
        init=list(bridge.demo_messages(0,1,7,50,100))
        self.assertEqual(len(init),2)
        self.assertEqual(init[0][2:5],bytes((0xB0,0,1)))
        self.assertEqual(init[1][2:5],bytes((0xC0,7,0)))

    def test_reject_bad_messages(self):
        for args in ((0xF0,1,0),(0x90,128,0),(0xC0,1,2)):
            with self.assertRaises(ValueError):
                bridge.frame(*args)

    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"midi.bin"
            subprocess.run([sys.executable,str(SCRIPT),"--dry-run",str(out)],
                           check=True,capture_output=True,text=True)
            data=out.read_bytes()
            self.assertEqual(len(data),24)
            self.assertEqual(data[14],0x90)
            self.assertEqual(data[20],0x80)


if __name__=="__main__":
    unittest.main()
