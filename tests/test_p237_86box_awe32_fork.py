"""Deterministic fail-closed tests for optional P237 fork integration."""
import importlib.util
import hashlib
import json
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


class ForkVs125AComparator(unittest.TestCase):
    """Synthetic-only contract fixtures: never masquerade as a Win95 run."""

    def make_case(self, folder: Path, *, ifatn=0x4300, shift_pcm=0,
                  guest_ok=True, sf2_native="ROM_ONLY"):
        p = folder
        fork = p/"fork.trace"
        native = p/"native.trace"
        # Port log format is exactly the fork's EMU8K_TRACE format:
        # 44.1k sample clock, pointer-select E22, voice-data port writes.
        def trace_text(value):
            return (f"100 E22 {((6<<5)|3):04X}\n"
                    f"101 620 1111\n"
                    f"101 E22 {((1<<5)|3):04X}\n"
                    f"102 E20 {value:04X}\n"
                    f"102 E22 {((4<<5)|3):04X}\n"
                    f"103 A22 2277\n")
        fork.write_text(trace_text(0x4300),encoding="utf8")
        native.write_text(trace_text(ifatn),encoding="utf8")
        def audio(path,amount):
            with wave.open(str(path),"wb") as w:
                w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
                raw=b"".join(struct.pack("<hh",1000+(i%97)+amount,
                                         -(1000+(i%97)+amount))
                             for i in range(6500))
                w.writeframes(raw)
        fw=p/"fork.wav";nw=p/"125a.wav"
        audio(fw,0);audio(nw,shift_pcm)
        metadata={"fork":{"rom_sha256":"a"*64,"sf2_sha256":"ROM_ONLY",
                          "midi":{"bank":16383,"program":39,"note":60,
                                  "velocity":100,"channel":0,"hold_frames":44100},
                          "effects":{"reverb":0,"chorus":0},
                          "chip_settings":{"rate_hz":44100,"voices":32}},
                  "native":{"rom_sha256":"a"*64,"sf2_sha256":sf2_native,
                            "midi":{"bank":16383,"program":39,"note":60,
                                    "velocity":100,"channel":0,"hold_frames":44100},
                            "effects":{"reverb":0,"chorus":0},
                            "chip_settings":{"rate_hz":44100,"voices":32}},
                  "fork_window":{"start_frame":100,"frames":5000},
                  "native_window":{"start_frame":100,"frames":5000}}
        report={"backend":"turican0/86Box-AWE32","tag":p237.TAG,
                "vm_is_disposable_copy_user_attested":True,
                "trace_sha256":p237.sha256(fork),
                "wav_sha256":p237.sha256(fw)}
        guest={"agent_launched_in_actual_win95":guest_ok,
               "original_creative_winmm_endpoint_selected":True,
               "audio_observed":True}
        def dump(name,obj):
            file=p/name
            file.write_text(json.dumps(obj),encoding="utf8")
            return file
        return (fork,native,fw,nw,dump("capture.json",report),
                dump("guest.json",guest),dump("match.json",metadata))

    def test_same_registers_and_pcm_report_exact_only_for_window(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder))
            result=p237.compare_real_fork_with_125a(*paths)
            self.assertEqual(result["registers"]["register_series_different"],0)
            self.assertTrue(result["digital_pcm"]["sample_exact_equal"])
            self.assertEqual(result["finding"],
                             "SAMPLE_EXACT_FOR_THIS_MATCHED_NOTE_WINDOW_ONLY")
            self.assertTrue(result["additional_real_AWE32_AWE64_hardware_validation_required"])
            self.assertFalse(result["release_fidelity_verified"])

    def test_ifatn_register_mismatch_identifies_driver_state_first(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder),ifatn=0x5300)
            result=p237.compare_real_fork_with_125a(*paths)
            self.assertEqual(result["registers"]["register_series_different"],1)
            self.assertEqual(result["registers"]["mismatches"][0]["register"],"IFATN")
            self.assertIn("REGISTER_OR_STATE",result["finding"])

    def test_same_registers_different_pcm_flags_chip_state_not_preset_hack(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder),shift_pcm=43)
            result=p237.compare_real_fork_with_125a(*paths)
            self.assertEqual(result["registers"]["register_series_different"],0)
            self.assertFalse(result["digital_pcm"]["sample_exact_equal"])
            self.assertGreater(result["digital_pcm"]["max_sample_delta_int16"],0)
            self.assertIn("DIGITAL_PCM_DIFFERS",result["finding"])

    def test_missing_guest_proof_or_matching_sf2_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder),guest_ok=False)
            with self.assertRaisesRegex(ValueError,"original Creative"):
                p237.compare_real_fork_with_125a(*paths)
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder),sf2_native="c"*64)
            with self.assertRaisesRegex(ValueError,"Input state differs.*sf2_sha256"):
                p237.compare_real_fork_with_125a(*paths)

    def test_fork_trace_tampering_rejected_before_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=self.make_case(Path(folder))
            paths[0].write_text(paths[0].read_text()+"444 E20 FFFF\n")
            with self.assertRaisesRegex(ValueError,"SHA256 mismatch"):
                p237.compare_real_fork_with_125a(*paths)

if __name__=="__main__":unittest.main()
