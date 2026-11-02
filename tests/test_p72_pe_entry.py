"""P72 regression for the original Win95 EXE wrong-entrypoint defect."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"tools"/"p72_verify_win95_entry.py"
spec=importlib.util.spec_from_file_location("p72_pe",PATH)
p72=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p72)

class PEEntry(unittest.TestCase):
    def test_mz_pe32_rva_and_imagebase(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"hello.exe"
            d=bytearray(256)
            d[:2]=b"MZ"
            struct.pack_into("<I",d,0x3C,0x80)
            d[0x80:0x84]=b"PE\x00\x00"
            struct.pack_into("<H",d,0x80+24,0x10b)
            struct.pack_into("<I",d,0x80+24+16,0x1095)
            struct.pack_into("<I",d,0x80+24+28,0x400000)
            p.write_bytes(d)
            self.assertEqual(p72.pe_entry_vma(p),0x401095)
    def test_stdcall_symbol_must_resolve(self):
        s="         U p68_entry\\n00401000 t _emit\\n00401095 T _p68_entry@0\\n"
        self.assertEqual(p72.nm_symbol_vma(s.replace("\\n","\n"),"_p68_entry@0"),0x401095)
        with self.assertRaises(ValueError):
            p72.nm_symbol_vma(s.replace("\\n","\n"),"p68_entry")
    def test_reject_older_wrong_text_start(self):
        symbol=p72.nm_symbol_vma("00401095 T _p68_entry@0","_p68_entry@0")
        self.assertNotEqual(0x401000,symbol)
if __name__=="__main__":
    unittest.main()
