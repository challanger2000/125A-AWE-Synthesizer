"""P87 compares independent captures; synthetic audio ONLY, no user assets."""
import json
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import numpy as np
from p87_audio_parity import compare, compare_directory, read_wav, NOTES

def synth_wav(path,gain=1.0,delay=0):
    n=44100
    signal=np.zeros((n,2),dtype="<i2")
    for i in range(700,n-delay):
        t=(i-700)/44100
        sample=int(round(10000*gain*np.sin(2*np.pi*333*t)*np.exp(-4*t)))
        signal[i+delay,:]=sample
    with wave.open(str(path),"wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(44100)
        file.writeframes(signal.tobytes())

class P87IndependentReference(unittest.TestCase):
    def test_nonzero_aligned_separately_recorded_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"creative.wav";b=Path(tmp)/"native.wav"
            synth_wav(a)
            synth_wav(b,gain=.91,delay=165)
            metrics=compare(a,b)
            self.assertGreater(metrics["waveform_correlation"],.97)
            self.assertAlmostEqual(metrics["level_difference_db"],.8,delta=.5)
            self.assertFalse(metrics["physical_hardware_1to1_proven"])
            self.assertEqual(len(metrics["spectrum_difference_db_by_band"]),9)
    def test_same_audio_rejected_even_if_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"creative.wav";b=Path(tmp)/"native.wav"
            synth_wav(a)
            b.write_bytes(a.read_bytes())
            with self.assertRaisesRegex(ValueError,"Duplicate WAV"):
                compare(a,b)
    def test_silent_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"a.wav"
            with wave.open(str(a),"wb") as file:
                file.setnchannels(2);file.setsampwidth(2)
                file.setframerate(44100);file.writeframes(bytes(44100*4))
            with self.assertRaisesRegex(ValueError,"Silent WAV"):
                read_wav(a)
    def test_all_six_matching_preset_note_pairs_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"original";b=Path(tmp)/"native"
            a.mkdir();b.mkdir()
            for program,note in NOTES:
                x=f"P{program}-N{note}.wav"
                synth_wav(a/x)
                synth_wav(b/x,gain=.95,delay=110)
            self.assertEqual(len(compare_directory(a,b)),6)
            (a/"P17-N42.wav").unlink()
            with self.assertRaisesRegex(ValueError,"exactly one"):
                compare_directory(a,b)

if __name__=="__main__":unittest.main()
