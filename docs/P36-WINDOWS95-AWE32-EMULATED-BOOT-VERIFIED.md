# P35/P36 — Finished Windows 95 image boots in PC emulator with AWE32 device

**2026-11-01. Research only; no change to the P26 VST3 or SF2 chip DSP.**

## Input

- Community Win95 OSR2.0 image `Windows95b_p9x-0.9.91_512MB.img.7z`, linked in https://github.com/copy/v86/discussions/1553
- Raw image exactly **536,870,912 bytes** with sha256 `fb685b36b15123af51bad9b68b3402671837065f330b33778bfc771ccfd33c26`
- The original Windows disk is only downloaded on **ephemeral GitHub Actions runners**, then deleted, and never committed or uploaded as an artifact.
- User wave ROM `awe32.raw` and private `Synth 512 Bank.sf2` are NOT on GitHub; P36 uses a **dummy** zeroed ROM exclusively to test device initialization.

## Actual runnable boots, with captured screenshots

| Test | Machine | Observed Win95 screen | Result |
|---|---|---|---|
| P35 https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41289168847 | QEMU Pentium / 64 MiB / offline IDE | Win95 graphical Windows Networking dialog: NE2000 Compatible 0000 not working | **PASS: Windows 95 graphical system running** |
| P36 https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41289600859 | DOSBox-X 2026.10.01 Pentium MMX / 64 MiB, `[sblaster] sbtype=awe32`, `[emu8k] memsize=8192`, 1 MiB dummy ROM, no network forwarding | Same Win95 graphical networking warning, capture at 22 and 47 seconds, DOSBox-X alive and actually rendering the guest | **PASS: Windows 95 boots with an AWE32-configured emulator** |

Both runs provide screenshot evidence. The NE2000 warning comes from the guest image's preinstalled network driver whose hardware is not present, **not from EMU8000**. It can be dismissed or the network device removed in the guest.

## Crucial limits

- Only **emulated AWE32 availability** is configured; no proof that the original Creative `SBAWE.VXD` has loaded.
- The guest image comes preconfigured for generic SB16, not the full original Creative AWE32 stack. Do not claim the original Win95 driver is installed or that SF2 programs 000 and 007 have been rendered.
- The sound is NOT compared; dummy wave ROM cannot be a credible audio test.
- The v86 community image has unknown Windows 95 license/provenance. Do not re-host it or include it in a released plugin package.

## Concrete next actions

1. Dismiss generic NE2000 warning, verify guest desktop.
2. Install a complete Creative Windows 95 AWE32 driver set into the guest, using legitimate archival installer materials that include `SB16AWE.INF`, `SBAWE.VXD`, `SBAWE32.DRV`, `AWEMAN32.DLL`. Examples documented at https://vogonsdrivers.com/index.php?catid=3 and Creative official `sbw9xup.exe` (driver update package, not necessarily full install).
3. Use 86Box instrumented port-writes or equivalent DOSBox-X EMU8000 ISA trace (and actual driver verification) to capture an original Win95 note-on at C3 velocity100 for both target programs.
4. Validate original 2/4 sample-RAM voices using P34 gate before comparing with P29 125A Win95 traces.
5. Only an observed register difference can justify altering the stable P26 sound.

**Status: BOOT/VM BLOCKER SOLVED. Original Creative VxD test NOT YET RUN.**


## P36 follow-up: actual EMU8000 detection confirmed

After configuring an isolated emulated NE2000 adapter with `backend=nothing`,
Windows 95 OSR2 continues to boot, and the Windows guest now displays its
DHCP client (no address is available, because the test has no network).
Importantly, DOSBox-X emits the **actual hardware setup log**:

```text
AWE32: EMU8000 on port 620h RAM 8192 KB
```

CI run: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41290110587

This positively verifies the emulator exposes EMU8000 register hardware
on the expected Creative base port and with 8 MiB RAM while Windows 95
starts. It **does not** mean the original Creative `SBAWE.VXD` is installed
or that the Win95 device manager successfully bound a driver.
The DHCP popup is a separate network warning; no host internet access
was enabled.

The guest image, ROM and SoundFont were never included in CI artifacts
or the source repository.
