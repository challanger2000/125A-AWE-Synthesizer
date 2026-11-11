"""Deterministic fail-closed tests for optional P237 fork integration."""
import importlib.util
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import wave
import zipfile

SCRIPT=Path(__file__).resolve().parents[1]/"tools/p237_86box_awe32_fork.py"
spec=importlib.util.spec_from_file_location("p237",SCRIPT)
p237=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p237)

class ForkTest(unittest.TestCase):
    def test_release_identity_pinned(self):
        self.assertEqual(len(p237.ZIP_SHA256),64)
        self.assertIn("turican0/86Box-AWE32",p237.RELEASE)
        self.assertIn("v6.0-AWE32-0.93",p237.RELEASE)

    def test_installer_rejects_modified_archive_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);arc=root/"fork.zip";dest=root/"out";dest.mkdir()
            with zipfile.ZipFile(arc,"w") as z:z.writestr("86Box.exe",b"MZ")
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                p237.install_archive(arc,dest)
            record=p237.install_archive(arc,dest,p237.sha256(arc))
            self.assertEqual(record["exe_sha256"],hashlib.sha256(b"MZ").hexdigest())
            self.assertTrue((dest/"P237-fork-install.json").is_file())
            with self.assertRaisesRegex(ValueError,"empty"):
                p237.install_archive(arc,dest,p237.sha256(arc))
            with zipfile.ZipFile(arc,"w") as z:z.writestr("../bad/86Box.exe",b"MZ")
            empty=root/"empty";empty.mkdir()
            with self.assertRaisesRegex(ValueError,"Unsafe path"):
                p237.install_archive(arc,empty,p237.sha256(arc))

    def test_valid_trace_and_digital_wav(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);trace=p/"trace";audio=p/"out.wav"
            trace.write_text("# header\n0 E22 0020\nR 0 620 0001\n4410 620 1234\n",encoding="utf8")
            with wave.open(str(audio),"wb") as f:
                f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100)
                f.writeframes(struct.pack("<h",32767)*8820)
            result=p237.audit_trace_and_wav(trace,audio)
            self.assertEqual(result["EMU8K_TRACE_writes"],2)
            self.assertEqual(result["chip_wav_frames"],4410)
            self.assertEqual(result["chip_pcm16_rail_samples"],8820)
            self.assertFalse(result["original_Creative_driver_activity_verified"])
            trace.write_text("100 E22 0020\n50 620 0001\n",encoding="utf8")
            with self.assertRaisesRegex(ValueError,"Nonmonotonic"):
                p237.audit_trace_and_wav(trace,audio)

    def test_rejects_missing_port_writes_and_empty_wav(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);trace=p/"trace";audio=p/"out.wav"
            trace.write_text("R 0 E22 0000\n",encoding="utf8")
            with self.assertRaisesRegex(ValueError,"No real guest"):
                p237.audit_trace_and_wav(trace,audio)
            trace.write_text("0 E22 0000\n",encoding="utf8")
            with wave.open(str(audio),"wb") as f:
                f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100);f.writeframes(b"\0"*400)
            with self.assertRaisesRegex(ValueError,"100ms"):
                p237.audit_trace_and_wav(trace,audio)

if __name__=="__main__":unittest.main()
