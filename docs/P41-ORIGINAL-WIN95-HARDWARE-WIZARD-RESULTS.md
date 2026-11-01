# P41 — Original Windows 95 Add New Hardware Wizard: measured results

**Date:** 2026-11-01. **Research-only. No release-code/audio change.**

## Confirmed working

- Windows 95 OSR2 boots in QEMU, and original Windows 95 Add New Hardware Wizard opens using genuine guest scancodes (no host hotkey contamination).
- The guest builds its first-install driver database and reaches the genuine **manufacturer/model list**. The P41 run #41297193661 shows the actual GUI and stable OS.
- The original 1997 Creative `SB16AWE.INF` has `Class=MEDIA`, manufacturer `Creative`, and mapping `CTL0021_Device,*CTL0021`, as confirmed from the original source.
- The original GUI's **Have Disk** button can be invoked. P41b run #41297570570 reached the `Install From Disk` dialog and entered the staged `C:\AWE32` path.

## Critical failed controls

1. Run #41297193661: original wizard defaulted to **Adaptec/SCSI**, and `s` key did not change the hardware class. Pressing Enter advanced SCSI installation. **No SCSI driver was intentionally completed**.
2. Run #41297570570: Have Disk on the **SCSI manufacturer page** rejected original Creative INF: Windows said the location does not contain information about *that* hardware. This is expected for a `Class=MEDIA` INF. The Creative INF is not shown to be corrupt.
3. Run #41297958300: experimental `Shift+Tab` then `s` and Enter on class-choice page unexpectedly **closed** the wizard. It did not select `Sound, video and game controllers`. Subsequent Have Disk keys were sent to the bare desktop. This was a **navigation mistake**, not a driver incompatibility.

The guest system `SYSTEM.DAT` still contains **zero** strings matching `SBAWE`, `CTL0021` or `AWEMAN`. Only staged driver files exist on disk. The original `SBAWE.VXD` is **not proven bound**, and neither bass patch has a driver-reference register trace.

## Next precise action

Select the **Sound, video and game controllers** hardware class via an independently verified guest input method, then choose Have Disk -> `C:\AWE32\SB16AWE.INF`, and choose the corresponding Creative AWE32 model. Validate the resulting PnP registry/device-manager binding. The staged QEMU guest lacks an emulated AWE32, so subsequently boot that disposable installed disk in AWE32-enabled DOSBox-X (or instrumented 86Box); only then compare note-on register writes. A Windows 95 OEM guest or proprietary source bits must not be checked into the repo.

## Release decision

**P26 remains untouched.** Passing CI tests which only boot Win95 and capture screenshots does **not** prove installed Creative drivers, real AWE32 MIDI behavior or 1:1 sound.
