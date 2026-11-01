"""Offline tests: ensure the 86Box trace patch fails closed on source changes."""
import importlib.util
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "tools/p45_86box_emu8k_trace.py"
spec = importlib.util.spec_from_file_location("p45_trace", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FIXTURE = (
    "#include <stdio.h>\n"
    "void\nemu8k_outw(uint16_t addr, uint16_t val, void *priv)\n{\n"
    "    emu8k_t *emu8k = (emu8k_t *) priv;\n"
    "    emu8k_update(emu8k);\n"
    "    if (addr == 0xe22) emu8k->cur_voice = val & 31;\n"
    "}\n"
)

class TestP45Trace(unittest.TestCase):
    def test_single_hook_and_fields(self):
        out = module.instrument(FIXTURE)
        self.assertEqual(out.count(module.MARKER), 1)
        self.assertEqual(out.count("p45_125a_trace_emu8k_write(emu8k, addr, val);"), 1)
        self.assertIn("sequence,wc,port,value,pointer,reg,voice,kind", out)
        self.assertIn("AWE_TRACE_CSV", out)
        self.assertIn('is_pointer ? "pointer" : "data"', out)

    def test_refuses_double_patch(self):
        with self.assertRaisesRegex(ValueError, "Already instrumented"):
            module.instrument(module.instrument(FIXTURE))

    def test_fail_closed_on_upstream_change(self):
        with self.assertRaisesRegex(ValueError, "signature"):
            module.instrument(FIXTURE.replace("uint16_t val", "uint32_t val"))
        with self.assertRaisesRegex(ValueError, "body changed"):
            module.instrument(FIXTURE.replace("emu8k_t *emu8k", "emu8k_t *chip"))
        with self.assertRaisesRegex(ValueError, "emu8k_update"):
            module.instrument(FIXTURE.replace("emu8k_update(emu8k);", "other();"))

if __name__ == "__main__":
    unittest.main()
