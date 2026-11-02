"""P83: no private SF2 in repository; test arbitrary banks and 28MiB limit."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from p55_stage_generated_sf2 import make_sf2
from p83_generic_sf2 import inspect_sf2, RAM_BYTES

def expand_smpl(sf2,target_bytes):
    """Create a standards-shaped test SF2 with an unchanged first 4K PCM."""
    if target_bytes%2:raise ValueError("even sample byte length required")
    p=sf2.find(b"smpl")
    if p<0:raise AssertionError("No smpl in synthetic fixture")
    old=struct.unpack_from("<I",sf2,p+4)[0]
    delta=target_bytes-old
    if delta<0:raise ValueError("target too small")
    out=bytearray(sf2[:p+8])+bytearray(sf2[p+8:p+8+old])
    out.extend(b"\0"*delta)
    out.extend(sf2[p+8+old:])
    struct.pack_into("<I",out,p+4,target_bytes)
    enclosing=sf2.find(b"sdta")-8
    n,=struct.unpack_from("<I",out,enclosing+4)
    struct.pack_into("<I",out,enclosing+4,n+delta)
    struct.pack_into("<I",out,4,len(out)-8)
    return bytes(out)

class GenericSF2(unittest.TestCase):
    def test_not_a_bank_specific_player(self):
        meta=inspect_sf2(make_sf2())
        self.assertEqual(meta["preset_count"],1)
        self.assertEqual(meta["presets"][0]["program"],0)
        self.assertTrue(meta["sample_memory_fits"])
        self.assertTrue(meta["samples_rewritten"] is False)
    def test_drum_bank_128_is_discovered(self):
        raw=bytearray(make_sf2())
        pos=raw.index(b"phdr")+8
        struct.pack_into("<H",raw,pos+22,128)
        meta=inspect_sf2(bytes(raw))
        self.assertEqual(meta["available_banks"],[128])
        self.assertTrue(meta["drum_bank_present"])
        self.assertTrue(meta["presets"][0]["percussion_bank"])
    def test_24_point_8_mb_sf2_fits_awe64_not_awe32(self):
        raw=expand_smpl(make_sf2(),24_800_000)
        gold=inspect_sf2(raw,RAM_BYTES["awe64_gold"])
        awe32=inspect_sf2(raw,RAM_BYTES["awe32"])
        self.assertTrue(gold["sample_memory_fits"])
        self.assertFalse(awe32["sample_memory_fits"])
        self.assertEqual(gold["sample_pcm_bytes"],24_800_000)
    def test_over_28_mib_is_rejected_as_hardware_limit(self):
        raw=expand_smpl(make_sf2(),RAM_BYTES["awe64_gold"]+2)
        r=inspect_sf2(raw)
        self.assertFalse(r["sample_memory_fits"])
        self.assertEqual(r["sample_memory_remaining_bytes"],-2)
    def test_invalid_riff_rejected(self):
        raw=bytearray(make_sf2())
        struct.pack_into("<I",raw,4,0)
        with self.assertRaisesRegex(ValueError,"RIFF length"):
            inspect_sf2(raw)

if __name__=="__main__":
    unittest.main()
