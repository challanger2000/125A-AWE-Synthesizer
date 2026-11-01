# P48b — Windows 95 detects original Creative AWE32 PnP and performs EMU8000 I/O

Date: 2026-11-01. Research only. P26 audio engine unchanged.

## Verified evidence

[GitHub Actions run 41349407124](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41349407124) succeeded, and its screenshot/text artifact was inspected.

- `win95-00015000.png`: 86Box P/I-P55T2P4 BIOS has first-boot CMOS checksum prompt; press F1 is sufficient to continue.
- `win95-00045004.png`: Win95 boots to its original NE2000 (0000) network warning.
- `win95-00050008.png`: after pressing OK once, Windows95 explicitly displays **New Hardware Found — Creative Advanced Wave Effects Synthesis for AWE 32**, with `Windows is installing the software for your new hardware.`
- `win95-00065008.png`: the Windows 95 desktop and native Welcome window appear.
- `win95-00125012.png`: desktop remains responsive; Welcome window still open.

The 86Box automation info reported `machine=p55t2p4`, `sound=sbawe32_pnp`, mounted IDE disk, and a 640x480 graphics frame (`bios_mode=18`). The ROMs and proprietary guest OS are strictly ephemeral and not included in the evidence artifact.

The P45 `emu8k_outw` hook records **47,197 raw word-write trace lines** over this guest boot, including **44,824 pointer-kind writes** and **2,372 data-kind writes** (one additional/incomplete line falls outside the simple kind count; do not claim exact category partition). In this P48b run no synthetic `iow` automation commands were sent, so the writes originate from real guest execution on the 86Box-emulated I/O bus. They are consistent with Windows guest PnP/Creative hardware initialization but **cannot yet be assigned solely to SBAWE.VXD**; driver image/module load state and MIDI note-on causation remain unproven.

## Remaining gates (do not conflate)

1. Inspect Windows 95 Device Manager binding/state for `Creative Advanced Wave Effects Synthesis for AWE 32` and validate original Creative VxD activation.
2. Stage a deterministic, original, tiny MIDI fixture in the disposable guest and send a note-on/note-off via the Windows MIDI API, while comparing idle-versus-note EMU8000 writes and audio output. Verify Windows MIDI Mapper routes to Creative AWE32 and not a generic MPU-401 or OPL FM path.
3. Compare voice register traces to P26's exact SF2/preset/velocity and then separately compare audio. None of this proves physical AWE32 1:1 fidelity without physical-hardware evidence.

## Safety

No Microsoft Win95 guest image, Creative driver binary, BIOS/ROM image, SF2, private MIDI data, or rendered sample audio is redistributed. CI artifacts contain screenshots and text only. The 86Box + original Win95 device is a *virtual hardware reference*, not a physical Sound Blaster AWE32 measurement.
