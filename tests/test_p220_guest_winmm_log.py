#!/usr/bin/env python3
"""P220 original guest WinMM log capacity test-of-test, no guest or SF2.

This is NOT an original Creative Win95 run. It prevents a deterministic
silent failure at 77*2=154 authentic prospective MIDI auditions: the
previous P67 max-8192-byte log limit would reject the complete guest log.
"""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from p67_read_guest_bridge_log import inspect,p220_expected_winmm_delivery
from p220_77_preset_capture_plan import BANK_SHA

def sample():
    cases=[]
    for p in range(78):
        if p==63:continue
        for m in ("DRY","MODFX"):
            cases.append({
                "id":f"P{p:03d}-{m}","program":p,
                "source_audio_pcm_from":"86box_wavetable_during_real_original_Win95",
                "original_emu8000_voice_write_delta":78,
                "note_off_sent_to_guest":True})
    report={"full_77_preset_soundfont_validated":True,
        "p220_original_win95_private_capture":{
            "private_sf2_sha256":BANK_SHA,"all_154_original_pcm_captured":True,
            "trials":cases}}
    return report

class GuestLogTests(unittest.TestCase):
    def test_p220_requires_exact_1394_message_count(self):
        plan=sample()
        self.assertEqual(p220_expected_winmm_delivery(plan),1394)
        raw=(b"P66 CRT-free original Creative Win95 bridge startup\r\n"
             b"SELECTED original Creative AWE Synth\r\n"
             b"READY COM1 115200 8N1\r\n"+b"MIDI DELIVERED\r\n"*1394)
        self.assertGreater(len(raw),8192)
        self.assertLess(len(raw),65536)
        with self.assertRaises(ValueError):
            inspect(raw)  # Legacy P67 cap unchanged.
        self.assertEqual(inspect(raw,max_bytes=65536)
                         ["creatives_midi_short_messages_delivered"],1394)
        self.assertFalse(inspect(raw,max_bytes=65536)["win95_agent_error"])
        self.assertNotEqual(inspect(raw[:-16],max_bytes=65536)
                            ["creatives_midi_short_messages_delivered"],1394)
    def test_no_unverified_widened_win95_log_cap(self):
        self.assertIsNone(p220_expected_winmm_delivery({}))
        fake=sample()
        for mutate in (
            lambda x:x["p220_original_win95_private_capture"].update(
                private_sf2_sha256="0"*64),
            lambda x:x["p220_original_win95_private_capture"].update(
                all_154_original_pcm_captured=False),
            lambda x:x["p220_original_win95_private_capture"]["trials"].pop(),
            lambda x:x["p220_original_win95_private_capture"]["trials"][2].update(
                program=63),
            lambda x:x["p220_original_win95_private_capture"]["trials"][4].update(
                original_emu8000_voice_write_delta=0),
            lambda x:x["p220_original_win95_private_capture"]["trials"][5].update(
                note_off_sent_to_guest=False),
        ):
            x=copy.deepcopy(fake);mutate(x)
            with self.assertRaises(ValueError):
                p220_expected_winmm_delivery(x)
        with self.assertRaises(ValueError):
            inspect(b"0"*65537,max_bytes=65536)
        with self.assertRaises(ValueError):
            inspect(b"0"*8193,max_bytes=10**8)
if __name__=="__main__":
    unittest.main()
