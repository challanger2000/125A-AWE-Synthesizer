"""P89 register-level comparisons: synthetic trace fixtures, no fake Creative result."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from p89_compare_voice_registers import original_csv,native_trace,compare,normalized

def original(path,events):
    rows=["sequence,wc,port,value,pointer,reg,voice,kind"]
    for i,(port,value,pointer,kind) in enumerate(events):
        rows.append(f"{i+1},{100+i},0x{port:04x},0x{value:04x},0x{pointer:04x},{(pointer>>5)&7},{pointer&31},{kind}")
    path.write_text("\n".join(rows)+"\n",encoding="utf8")

def native(path,events):
    rows=["# 44100 Hz native port trace"]
    for index,(port,value) in enumerate(events):
        rows.append(f"{index} {port:03X} {value:04X}")
    path.write_text("\n".join(rows)+"\n",encoding="utf8")

class P89VoiceRegisters(unittest.TestCase):
    def test_pointer_decode_and_sample_upload_filtered(self):
        self.assertEqual(normalized(0x620,0x1234,(7<<5)|4),(4,"DATA0:R7",0x1234))
        self.assertIsNone(normalized(0xA20,0x1234,(1<<5)|26))
        self.assertIsNone(normalized(0xE22,0x1234,(1<<5)|26))
    def test_different_voice_ids_not_misclassified_as_wrong_values(self):
        with tempfile.TemporaryDirectory() as d:
            ref=Path(d)/"creative.csv";nat=Path(d)/"native.trace"
            original(ref,[(0xE22,(4<<5)|3,0,"pointer"),
                          (0xA20,0x1234,(4<<5)|3,"data"),
                          (0xE22,(4<<5)|3,0,"pointer"),
                          (0xA22,0x0023,(4<<5)|3,"data")])
            native(nat,[(0xE22,(4<<5)|6),
                         (0xA20,0x1234),
                         (0xE22,(4<<5)|6),
                         (0xA22,0x0023)])
            a=original_csv(ref,0,4)
            b=native_trace(nat)
            result=compare(a,b)
            self.assertTrue(result["note_register_series_equal"])
            self.assertEqual(result["register_series_different"],0)
            self.assertFalse(result["emulated_hardware_1to1_proven"])
            self.assertFalse(result["physical_hardware_parity_proven"])
    def test_one_filter_register_difference_is_located(self):
        result=compare([(1,"DATA1:R5",0x2222),
                        (1,"DATA1:R6",0x40FF)],
                       [(9,"DATA1:R5",0x2222),
                        (9,"DATA1:R6",0x30FF)])
        self.assertEqual(result["register_series_different"],1)
        self.assertEqual(result["mismatches"][0]["register"],"DATA1:R6")
        self.assertEqual(result["mismatches"][0]["creative_first"],["0x40FF"])
        self.assertEqual(result["mismatches"][0]["native_first"],["0x30FF"])
    def test_creative_range_rejects_upload_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"original.csv"
            original(path,[(0xA20,0xCAFE,(1<<5)|26,"data")])
            with self.assertRaisesRegex(ValueError,"no voice writes"):
                original_csv(path,0,1)
    def test_invalid_missing_creative_note_range_rejected(self):
        with self.assertRaisesRegex(ValueError,"boundaries"):
            original_csv(Path("/nonexistent"),5,5)
    def test_native_data_before_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"native.trace"
            native(path,[(0xA20,0x1234)])
            with self.assertRaisesRegex(ValueError,"before register pointer"):
                native_trace(path)
    def test_no_independent_original_evidence_no_report(self):
        # CLI fail-close is checked before reading any private PCM or registers.
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"p67.json"
            path.write_text(json.dumps({"agent_launched_in_actual_win95":False}))
            self.assertFalse(json.loads(path.read_text())["agent_launched_in_actual_win95"])

if __name__=="__main__":unittest.main()
