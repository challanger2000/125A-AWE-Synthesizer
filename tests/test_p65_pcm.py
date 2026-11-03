import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools"/"p65_pcm_receiver.py"
spec=importlib.util.spec_from_file_location("p65pcm",P)
pcm=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcm)


class PcmTest(unittest.TestCase):
    def packet(self,seq,value):
        h=pcm.HEADER.pack(b"AWE0",seq,pcm.FRAME_COUNT,44100)
        return h+struct.pack("<"+"h"*pcm.FRAME_COUNT*2,
                 *([value]*(pcm.FRAME_COUNT*2)))

    def test_packets_and_drops(self):
        x=pcm.PcmStats()
        x.accept(self.packet(4,0))
        x.accept(self.packet(6,1000))
        report=x.report()
        self.assertEqual(report["sequence_gaps"],1)
        self.assertEqual(report["frames"],1960)
        self.assertEqual(report["nonzero_frames"],980)
        self.assertTrue(report["actual_emu8000_pcm_observed"])
        self.assertLess(report["peak_dbfs"],0)

    def test_corrupt_format_rejected(self):
        x=pcm.PcmStats()
        with self.assertRaises(ValueError):
            x.accept(b"garbage")
        b=bytearray(self.packet(0,0))
        b[0]=0
        with self.assertRaises(ValueError):
            x.accept(bytes(b))

    def test_source_instrumenter(self):
        source=(ROOT/"tools"/"p65_86box_pcm_tap.py").read_text()
        self.assertIn("O_WRONLY|O_NONBLOCK",source)
        self.assertIn("signal(SIGPIPE,SIG_IGN)",source)


if __name__=="__main__":
    unittest.main()
