#!/usr/bin/env python3
"""Inject an opt-in, raw EMU8000 I/O-write tracer into an external 86Box source copy.

Research-only: no 86Box source or third-party ROM/Windows driver is bundled.
This instrument logs writes to 86Box's EMU8000 I/O callbacks, NOT physical
AWE32 hardware measurements. An actual Win95+Creative driver+86Box run is
required to obtain data. Never publish sampled proprietary soundbank data.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

MARKER = "P45_125A_EMU8K_TRACE"
FUNCTION = "void\nemu8k_outw(uint16_t addr, uint16_t val, void *priv)\n{\n"
UPDATE = "    emu8k_update(emu8k);\n"

HELPER = r'''
/* P45_125A_EMU8K_TRACE: opt-in raw EMU8000 port writes.
   Set AWE_TRACE_CSV to a local private file path in the 86Box host process.
   Not a hardware gold standard; no sample payload/ROM data are included by
   the patch itself. The trace may contain guest register/data writes. */
static void
p45_125a_trace_emu8k_write(const emu8k_t *emu8k, uint16_t port, uint16_t value)
{
    static int attempted = 0;
    static FILE *fp = NULL;
    static unsigned long long sequence = 0;
    if (!attempted) {
        attempted = 1;
        const char *path = getenv("AWE_TRACE_CSV");
        if (path && *path) {
            fp = fopen(path, "wb");
            if (fp) {
                fprintf(fp, "sequence,wc,port,value,pointer,reg,voice,kind\n");
            } else {
                fprintf(stderr, "P45: cannot open AWE_TRACE_CSV: %s\n", path);
            }
        }
    }
    if (!fp)
        return;

    /* Register-pointer writes use the new pointer; data writes use the
       active pointer as it existed immediately before this I/O access. */
    const int is_pointer = ((port & 0xF02) == 0xE02);
    const unsigned int pointer = is_pointer ? value
        : (((unsigned int) emu8k->cur_reg << 5) | emu8k->cur_voice);
    ++sequence;
    fprintf(fp, "%llu,%llu,0x%04x,0x%04x,0x%04x,%u,%u,%s\n",
            sequence, (unsigned long long) emu8k->wc,
            (unsigned int) port, (unsigned int) value,
            pointer, (pointer >> 5) & 7, pointer & 31,
            is_pointer ? "pointer" : "data");
    /* P51 research precision: make every complete port-write record
       visible to the host automation reader immediately. Without this,
       P50's first-second register counts were misleading because the
       stdio buffer flush interval was 128 writes. This is enabled only
       when AWE_TRACE_CSV is set. */
    fflush(fp);
}
'''

def instrument(source: str) -> str:
    if MARKER in source:
        raise ValueError("Already instrumented; refusing double insertion")
    if source.count(FUNCTION) != 1:
        raise ValueError("Expected unique 86Box emu8k_outw signature is missing")
    pre, body = source.split(FUNCTION, 1)
    if not body.startswith("    emu8k_t *emu8k = (emu8k_t *) priv;"):
        raise ValueError("86Box function body changed; inspect new upstream first")
    if body.count(UPDATE) != 1:
        raise ValueError("Expected unique emu8k_update() in outw body is missing")
    body = body.replace(UPDATE, UPDATE + "    p45_125a_trace_emu8k_write(emu8k, addr, val);\n", 1)
    return pre + HELPER + "\n" + FUNCTION + body

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True, help="Original external src/sound/snd_emu8k.c")
    p.add_argument("--out", type=Path, required=True, help="Destination patched C file (not in-place)")
    args = p.parse_args()
    src = args.source.resolve()
    dst = args.out.resolve()
    if src == dst:
        p.error("Use a separate output file; original 86Box source stays intact")
    original = src.read_text(encoding="utf-8")
    transformed = instrument(original)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(transformed, encoding="utf-8", newline="\n")
    print("Original 86Box source SHA256:", hashlib.sha256(original.encode("utf-8")).hexdigest())
    print("Patched independent copy:", dst)
    print("Trace active ONLY with AWE_TRACE_CSV set on the 86Box host")

if __name__ == "__main__":
    main()
