"""P75: exact private bass patch lookup, no user SF2 in repository."""
import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from p75_private_sf2 import inspect
from p55_stage_generated_sf2 import make_sf2
class P75PrivateBank(unittest.TestCase):
    def test_generated_bank_not_mistaken_for_user_basses(self):
        with self.assertRaisesRegex(ValueError,"MIDI program"):
            inspect(make_sf2())
    def test_wrong_riff_length(self):
        raw=bytearray(make_sf2())
        struct.pack_into("<I",raw,4,1)
        with self.assertRaisesRegex(ValueError,"RIFF length"):
            inspect(raw)
    def test_non_soundfont(self):
        with self.assertRaisesRegex(ValueError,"Not a SoundFont"):
            inspect(b"none")
