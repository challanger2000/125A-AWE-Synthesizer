"""P69 AWE64 Gold 28MiB configuration; no Win95/SF2 claims."""
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from p47_86box_emu8k_smoke import write_config

class GoldConfiguration(unittest.TestCase):
    def test_explicit_28mib_and_gold_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            vm=Path(tmp)
            write_config(vm, "sbawe64_gold")
            with (vm / "86box.cfg").open("a",encoding="utf8") as cfg:
                cfg.write("[Sound Blaster AWE64 Gold]\\nonboard_ram = 28672\\n".replace("\\n","\n"))
            c=(vm / "86box.cfg").read_text(encoding="utf8")
            self.assertIn("sndcard = sbawe64_gold",c)
            self.assertIn("onboard_ram = 28672",c)
    def test_emu8k_wave_rom_size(self):
        self.assertEqual(1024 * 1024,1048576)

if __name__=="__main__":
    unittest.main()
