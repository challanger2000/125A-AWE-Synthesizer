"""P76 private WAV export tests; use synthetic wave test data only."""
import importlib.util, math, struct, tempfile, unittest, wave
from pathlib import Path
path=Path(__file__).resolve().parents[1]/"tools"/"p76_export_private_wav.py"
spec=importlib.util.spec_from_file_location("p76",path)
p76=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p76)

def trial():
    return {"p75_private_sample_upload_plausible":True,
            "p64_original_win95_midi":{
        "p75_original_private_sf2_test":True,
        "original_creative_midi_activity_register_write_delta":80,
        "p75_program_results":[{"program":0,"nonzero_audio":True},
                               {"program":7,"nonzero_audio":True}]}}

def make_pair(folder, signal):
    for name,_ in p76.CAPTURE_DIRS.values():
        pass
    for dirname,_ in p76.CAPTURE_DIRS.values():
        p=folder/dirname
        p.mkdir()
        with wave.open(str(p/"86box-wavetable.wav"),"wb") as f:
            f.setnchannels(2); f.setsampwidth(2); f.setframerate(44100)
            x=[int(5000*math.sin(i*0.08)) if signal else 0 for i in range(25000)]
            y=[n for v in x for n in (v,v)]
            f.writeframes(struct.pack("<"+"h"*len(y),*y))

class ExportTests(unittest.TestCase):
    def test_two_exact_copies(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);make_pair(root,True)
            result=p76.export(root,root/"private",trial())
            self.assertEqual(len(result["private_local_exports"]),2)
            for name,dest in p76.CAPTURE_DIRS.values():
                self.assertEqual((root/name/"86box-wavetable.wav").read_bytes(),
                                 (root/"private"/dest).read_bytes())
    def test_refuse_synthetic_or_silent(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(ValueError):
                p76.export(root,root/"private",{})
            make_pair(root,False)
            with self.assertRaisesRegex(ValueError,"Silent"):
                p76.export(root,root/"private",trial())
            self.assertFalse((root/"private").exists())
if __name__=="__main__":
    unittest.main()
