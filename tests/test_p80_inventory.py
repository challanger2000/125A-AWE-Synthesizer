"""P80 public regression uses only newly synthesized test SoundFonts."""
import importlib.util
import struct
import unittest
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("p80",root/"tools"/"p80_full_sf2_inventory.py")
p80=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p80)
spec2=importlib.util.spec_from_file_location("p55",root/"tools"/"p55_stage_generated_sf2.py")
p55=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(p55)

class FullSoundFont(unittest.TestCase):
    def test_rejects_generated_one_preset_bank(self):
        with self.assertRaisesRegex(ValueError,"Wrong preset count"):
            p80.inventory(p55.make_sf2())
    def test_rejects_bad_riff_size(self):
        raw=bytearray(p55.make_sf2())
        struct.pack_into("<I",raw,4,1)
        with self.assertRaisesRegex(ValueError,"RIFF file size"):
            p80.inventory(bytes(raw))
    def test_exact_program_number_set(self):
        self.assertEqual(len(p80.PROGRAMS),77)
        self.assertNotIn(63,p80.PROGRAMS)
        self.assertIn(0,p80.PROGRAMS)
        self.assertIn(7,p80.PROGRAMS)
        self.assertIn(77,p80.PROGRAMS)

if __name__=="__main__":
    unittest.main()
