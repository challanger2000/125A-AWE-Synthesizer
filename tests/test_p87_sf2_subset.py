"""P87 exact SF2 sample-zone reduction is tested with entirely synthetic PCM."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from p55_stage_generated_sf2 import make_sf2
from p83_generic_sf2 import inspect_sf2
from p87_extract_private_sf2_subset import subset

class P87OriginalSampleIntegrity(unittest.TestCase):
    def test_single_preset_preserves_original_synthetic_pcm(self):
        original=make_sf2()
        reduced=subset(original,programs=(0,),notes=(36,),bank=0)
        before=inspect_sf2(original)
        after=inspect_sf2(reduced)
        self.assertEqual(after["preset_count"],1)
        self.assertEqual(after["sample_count"],1)
        self.assertEqual(after["presets"][0]["name"],"P55 Sine Tone")
        self.assertEqual(before["sample_pcm_bytes"],after["sample_pcm_bytes"])
        self.assertLessEqual(len(reduced),len(original)+128)
        # The source has exactly one sample; sample bytes must be unchanged.
        def sample_chunk(raw):
            start=raw.index(b"smpl")
            length=int.from_bytes(raw[start+4:start+8],"little")
            return raw[start+8:start+8+length]
        self.assertEqual(sample_chunk(original),sample_chunk(reduced))
    def test_refuses_missing_program(self):
        with self.assertRaisesRegex(ValueError,"Missing or ambiguous"):
            subset(make_sf2(),programs=(17,),notes=(36,))
    def test_refuses_no_matching_note_zone(self):
        # The synthetic fixture's instrument zone covers all keys, so 127
        # remains valid. Missing program is the reliable negative case.
        with self.assertRaisesRegex(ValueError,"Expected SF2"):
            subset(b"invalid",programs=(0,),notes=(36,))

if __name__=="__main__":unittest.main()
