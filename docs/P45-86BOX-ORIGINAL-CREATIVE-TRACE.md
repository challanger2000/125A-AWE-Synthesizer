# P45 — instrumenting EMU8000 writes from original Creative drivers inside 86Box

**Research only.** 86Box emulates AWE32/EMU8000 hardware; it is *not* a physical AWE32 measurement standard. Its own EMU8000 source acknowledges approximations in chorus processing. The original Windows 95 Creative driver must run inside an appropriately configured 86Box VM with the AWE32 ISA device actually present. Merely selecting the INF in generic QEMU is insufficient.

## Confirmed upstream interception point

86Box/86Box `src/sound/snd_emu8k.c` exports `emu8k_outw(uint16_t addr, uint16_t val, void *priv)` and `emu8k_outb` delegates to it. The EMU8000 pointer register is addressed at an EMU I/O port ending in `0xE02` (e.g. 0xE22 in a typical 0x220 Sound Blaster base); data writes use the other I/O addresses. The instrumentation records both pointer and data writes, in sequence, with original raw address, value, pointer/register/voice, and emulated sample-clock counter `wc`.

The opt-in patcher lives at `tools/p45_86box_emu8k_trace.py`. It patches a **separate copy** of the external 86Box C source, refusing both double injection and unexpected source signatures; no 86Box source files or proprietary OS/ROM/driver files are shipped in this repository.

## Example local research usage (not a verified end-to-end result)

```bash
python tools/p45_86box_emu8k_trace.py \
  --source /external/86Box/src/sound/snd_emu8k.c \
  --out /external/86Box/src/sound/snd_emu8k-instrumented.c
```

The researcher must review and substitute the instrumented copy when building a private 86Box version; the script intentionally **does not** overwrite the 86Box checkout. Set environment variable `AWE_TRACE_CSV` to a local absolute file path in the **86Box host process**. If unset, the trace is disabled. The CSV is private and includes raw register writes; do not publish copyrighted sample banks or proprietary guest images.

## Required proof before calling a trace a Creative driver reference

1. Configure a known 86Box revision, ROM set, ISA AWE32 card, port/IRQ/DMA and guest Win95 image (none committed).
2. Verify original Creative `SBAWE.VXD` loads and its device is bound, not merely copied to `WINDOWS/SYSTEM`.
3. Load the exact SF2 with the original Creative software, verify the exact preset/bank mappings, and perform a deterministic note-on/note-off sequence separately for programs 000 and 007.
4. Store exact patch identity, MIDI note, velocity, pitch-bend, sample rate and driver revision in a local manifest. Run an idle trace and a note trace to distinguish driver initialization from note-on writes.
5. Parse and compare the raw register sequence to P26, then *separately* investigate audio fidelity. A 86Box-versus-P26 match is **not** physical AWE32-versus-P26 verification.

**Current status:** P43 selected the correct original Creative AWE32 synthesizer and reached the Finish page. P44 performs its controlled confirmation. No genuine register comparison has yet been obtained.

## Exact 86Box AWE32 PnP target (verified upstream source)

The correct target for the original `CTL0021` synthesis logical-device ID is the **AWE32 PnP** family, not an assumed generic/non-PnP Sound Blaster. The Linux ALSA ISA PnP device table maps AWE32 family cards to a `CTL0021` wavetable logical device.

In current 86Box `src/sound/snd_sb.c`, the exact device internal name is `sbawe32_pnp`. It requires **both** of the external 86Box ROM assets:

- `roms/sound/creative/awe32.raw` — mandatory EMU8000 Wave ROM (`EMU8K_ROM_PATH` in `snd_emu8k.h`).
- `roms/sound/creative/CT3980 PnP.BIN` — mandatory AWE32 PnP ID ROM (`PNP_ROM_SB_AWE32_PNP` in `snd_sb.c`).

The relevant upstream availability guard is `sb_awe32_pnp_available() == rom_present(EMU8K_ROM_PATH) && rom_present(PNP_ROM_SB_AWE32_PNP)`. These ROM images are not bundled in the 125A repo or any CI artifact. Runtime matching of the actual PnP subdevice ID still needs confirmation in the emulator.

Sources: [86Box AWE32 hardware implementation](https://github.com/86Box/86Box/blob/master/src/sound/snd_sb.c), [86Box EMU8000 ROM requirement](https://github.com/86Box/86Box/blob/master/src/include/86box/snd_emu8k.h), [Linux ALSA AWE32 PnP ID mapping](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/master/sound/isa/sb/sb16.c).
