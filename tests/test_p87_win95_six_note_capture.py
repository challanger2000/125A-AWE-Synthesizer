"""P87 six-note Win95 MIDI capture transport mock; never a claim of Win95 audio."""
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import p87_win95_six_note_capture as p87

def fake_wav(path):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
        w.writeframes(b"\x20\x10\x00\x00"*25000)

class P87SixCreativeAuditions(unittest.TestCase):
    def valid_report(self):
        return {"p84_universal_sf2_test":True,
                "p75_private_sample_upload_plausible":True,
                "hardware":"sbawe64_gold","sample_ram_kib":28672}
    def test_six_independently_named_original_driver_capture_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            commands=[]
            def send(conn,command):
                commands.append(command)
                if command.startswith("audio start "):
                    folder=Path(command[len("audio start "):])
                    fake_wav(folder/"test-wavetable.wav")
                return {}
            with patch.object(p87,"connect_linux_86box_fifo",
                              side_effect=lambda _:os.open(os.devnull,os.O_WRONLY)), \
                 patch.object(p87,"send_paced_frame",side_effect=lambda fd,payload,conn,send:len(payload)):
                report=self.valid_report()
                result=p87.capture_six(None,send,root/"pipe",report,root/"out",root/"private")
            self.assertEqual(result["validated_wavs"],6)
            self.assertEqual(len(set(x["file"] for x in result["auditions"])),6)
            self.assertEqual({x["program"] for x in result["auditions"]},{0,17})
            self.assertEqual({x["note"] for x in result["auditions"]},{36,38,42})
            self.assertEqual(sum(x.startswith("audio start ") for x in commands),6)
            self.assertEqual(commands.count("audio stop"),6)
            self.assertTrue(all(Path(x["file"]).is_file() for x in result["auditions"]))
            self.assertFalse(result["physical_hardware_parity_proven"])
    def test_unverified_original_sample_upload_rejected(self):
        r=self.valid_report();r["p75_private_sample_upload_plausible"]=False
        with self.assertRaisesRegex(ValueError,"upload"):
            p87.capture_six(None,None,Path("."),r,Path("."),Path("."))
    def test_wrong_hardware_rejected(self):
        r=self.valid_report();r["hardware"]="sbawe32_pnp"
        with self.assertRaisesRegex(ValueError,"AWE64 Gold"):
            p87.capture_six(None,None,Path("."),r,Path("."),Path("."))

if __name__=="__main__":unittest.main()
