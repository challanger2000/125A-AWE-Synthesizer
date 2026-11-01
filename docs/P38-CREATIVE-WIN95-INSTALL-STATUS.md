# P37–P38: Win95 original AWE32 driver-install experiment

**Research status 2026-11-01:** Windows 95 original Creative driver files staged and Win95 boots, but **the original SBAWE.VXD has not been proven loaded/bound to the emulated EMU8000**. This is not hardware fidelity evidence and does not justify a P26 sound change.

## Verified machine and missing components

The 512 MiB preinstalled Win95 OSR2 system from v86 boots on the official DOSBox-X (2026.10.01) with `sbtype=awe32`, EMU8000 port 0x620 and 8192 KiB RAM. P37 inspected its FAT16 partition (MBR start LBA 63, 32256-byte offset) and found only SB16 components (`SB16.VXD` and `SB16SND.DRV`). The original Creative AWE32 `SBAWE.VXD`, `SBAWE32.DRV`, `AWEMAN32.DLL` and `SB16AWE.INF` were **all absent**. Windows-95 SetupX and Rundll are present.

## Complete original Creative package

Matched Creative Windows 95 AWE32 package (1997–98) from public archived file mirror, with `SB16AWE.INF` section `CTL0021_Device`:

- `SBAWE.VXD`, `SBAWE32.DRV`, `AWEMAN.DLL`, `AWEMAN32.DLL`
- `SB16AWE.INF`, `SYNTHGM.SBK` and original SB16 dependencies, 21 files total
- Source and version: https://sobac.com/ZIPfiles/Operating%20Systems/Windows/Drivers/Audio/SB16%20CT2940/
- These versions are newer than the ADIP 3.01 1996 VxD used for P34's static binary audit; register comparisons must pin this **actual installed 1998 driver revision**, not assume matching 1996 binaries.

The package is downloaded solely to a disposable CI VM; neither vendor files nor the Microsoft OS disk are committed or uploaded. Original private `awe32.raw` and `Synth 512 Bank.sf2` do not participate in CI.

## Actual execution results

| Step | Result |
| --- | --- |
| P37 FAT inventory | PASS: no preinstalled AWE32 stack |
| P38 initial SetupX via `WIN.INI run=` with staged `C:\AWE32` | Guest boots; no files copied to system, registry has no AWE32 markers |
| P38b direct placement of original Creative files in `C:\WINDOWS\SYSTEM`; `[386Enh] device=C:\WINDOWS\SYSTEM\SBAWE.VXD` startup entry | PASS: guest still boots; system contains `SBAWE.VXD`, `SBAWE32.DRV`, `AWEMAN32.DLL` after VM execution. **No** verified driver bind. |
| P38c additionally invoke `SETUPX.DLL,InstallHinfSection CTL0021_Device 132 ...` via automated Windows GUI keyboard | CI boot/execution successful, but **no** persistent `SBAWE`, `CTL0021` or `AWEMAN` registry marker and no original MIDI/EMU8000 note trace. No binding established. |

Known P38c run: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41291956884. Output is screenshot, test log, and JSON only.

The Win95 original driver package's `SB16AWE.INF` `CTL0021_Device` is a **device installation section** using `HKR` relative keys; simply invoking it without enumerating/binding an AWE32 hardware device does not guarantee an installed MIDI device.

## Accurate conclusion

**Working now:** real Windows 95 boots with a live emulated AWE32, authentic Creative files are staged on its disk and the guest stays functional.

**Still missing:** Windows Device Manager / Add New Hardware association of the legacy non-PnP AWE32 driver, followed by an original VxD MIDI test. There is no valid original 000/007 register trace and no reason to choose between P33 additive and legacy-fill yet.

**Do not:** treat CI SUCCESS as loaded original Creative driver, upload private SoundFont/ROM, or alter production P26 DSP based on installation-stage observations. The trial and its artifacts are isolated from the released plugin.
