"""P84 simulated transport-only regression; not proof of real Creative sound."""
import os
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLS))
import p64_original_win95_midi_trial as p64
from p84_export_universal_wav import export,safe_name

def wav_fixture(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
        w.writeframes(struct.pack("<hh",3200,-3200)*25000)

class UniversalCreativeAudition(unittest.TestCase):
    def test_label_sanitization(self):
        self.assertEqual(safe_name("You Process 'Em"),"You Process _Em")
        self.assertEqual(safe_name(""),"Unnamed")
        self.assertEqual(safe_name("Kick:/Snare?"),"Kick__Snare_")
    def test_arbitrary_programs_and_note_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            trace=root/"emu.csv"
            trace.write_text("reg,data\n",encoding="utf8")
            sent=[]
            def send(conn,cmd):
                sent.append(cmd)
                if cmd.startswith("audio start "):
                    dest=Path(cmd.removeprefix("audio start "))
                    wav_fixture(dest/"fake-wavetable.wav")
                if cmd=="audio stop":
                    with trace.open("a") as logfile:logfile.write("1,2\n")
                return {}
            def screenshot(conn,out,name,report):
                pass
            report={"p84_universal_sf2_test":True,
                    "p75_private_sample_upload_plausible":True,
                    "p84_selected_presets":[
                        {"bank":0,"program":0,"name":"StandardStuff"},
                        {"bank":0,"program":17,"name":"Industrial"}],
                    "p84_creative_user_bank":1}
            with patch.object(p64,"connect_linux_86box_fifo",side_effect=lambda path:os.open(os.devnull,os.O_WRONLY)), \
                 patch.object(p64,"analyze_wav",side_effect=lambda wav,note:{"window_rms_dbfs":-20}):
                trial=p64.run_trial(None,root,trace,root/"midi",send,None,None,screenshot,report,
                                   programs=(0,17),note=36,creative_bank=1,
                                   preset_names={0:"StandardStuff",17:"Industrial"})
            self.assertEqual([x["program"] for x in trial["p75_program_results"]],[0,17])
            self.assertEqual([x["name"] for x in trial["p75_program_results"]],["StandardStuff","Industrial"])
            self.assertTrue(all(x["nonzero_audio"] for x in trial["p75_program_results"]))
            self.assertIn("step 1200",sent)
            delivered=export(root,root/"private",report)
            self.assertEqual(len(delivered["private_wavs"]),2)
            self.assertTrue(all(Path(x["path"]).is_file() for x in delivered["private_wavs"]))
            self.assertTrue(any("P017-Industrial" in x["path"] for x in delivered["private_wavs"]))
    def test_reject_unverified_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"upload"):
                export(Path(directory),Path(directory)/"private",{"p84_universal_sf2_test":True})
if __name__=="__main__":
    unittest.main()
