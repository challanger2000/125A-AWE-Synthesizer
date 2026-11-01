# P32 – Important authenticity conflict in SF2 preset composition (2026-11-01)

**Research status, NOT merged. Current P26 audio and production VST3 are unchanged.**

## New factual result from the user's actual bank

The genuine private 555,754-byte `Synth 512 Bank.sf2` was parsed locally (bank=0, MIDI key=48, velocity=100). The original binary and PCM were **not** committed. The audit compares two explicit interpretations:

- **P26 SF2 specification:** add preset generator offsets to the instrument's effective values; when absent, start from SF2 default; clamp as implemented in P26.
- **Legacy fill-only candidate:** preset values fill only missing instrument generators, as the original AWE32Emu `SoundFont.cpp` uses. That behavior is documented from register traces of **SF1** material (not yet proven for this 2.01 SF2 on real Win95).

Six matched sample layers (two `Grungy Ramp Bass`, four `TX81Z Lately Bass`) differ in **both** candidate models. Examples:

| Generator | Instrument | Preset | Legacy fill | P26 add |
| --- | ---: | ---: | ---: | ---: |
| TX81Z Lately Bass filterQ | 100 | -110 | 100 | -10 |
| TX81Z Lately Bass chorus | 0 | +400 (or +300) | 0 | 400 (or 300) |
| TX81Z Lately Bass attackVolEnv | -7973 | -3986 | -7973 | -11959 |
| TX81Z Lately Bass delayVolEnv | *absent* | -3986 | -3986 | -12000 |
| TX81Z Lately Bass fineTune | -5 | -1 | -5 | -6 |
| Grungy Ramp Bass chorus | 0 | +500 | 0 | 500 |
| Grungy Ramp Bass attackVolEnv | -4842 | -3986 | -4842 | -8828 |
| Grungy Ramp Bass delayVolEnv | *absent* | -3986 | -3986 | -12000 |

The **~100 ms delay in P25** was indeed consistent with `delayVolEnv=-3986` interpreted as absolute. **P26 removed that delay**, making the waveform closer to FluidSynth. But **we have not yet established whether the physical AWE32/Win95 driver would apply the SF2 preset offset or fill-only rule for this bank.** The previously claimed P26 "original sound fixed" is therefore **not a hardware-fidelity proof**.

## Upstream evidence and scope of its claims

- Original project `turican0/AWE32Emu`, `AWE32Emu/src/SoundFont.cpp`: unconditional `r.gen.FillFrom(presetGen)`.
- Its `docs/re-notes/tests.md` shows a *measured* Win95 `SBAWE.VXD` comparison, notably program 97 in **CRAZY**: `coarseTune` present both at preset and instrument levels; instrument wins, all 58 notes matched after `FillFrom` was used. This is evidence for its test bank, not specifically the user's SF2.
- Its `docs/TESTING.md` matrix reports 32/32 register parity for 10 cases including a custom SF1 `SYNTH02S.SBK` Win95 bank. We cannot infer from those figures that `SF2 2.01` follows the exact same generator precedence.
- The 1996 original DOS Creative SDK `SF2LIB` accepted the user's bank only with a **temporary** v2.00 header, but P31's automated-note run produced invalid/inaudible traces. The proper reference for the plug-in's `Win95` driver mode remains the authentic `SBAWE.VXD` under an instrumented Win95 guest.

## Independent new audit tool

`tools/p32_sf2_preset_merge_audit.py` reads a local SF2 and prints both candidate generator sets per matching sample layer. It **does not modify any bank**, never uploads data, and does not affect audio DSP.

Usage (private workstation, file never committed):

```powershell
python tools/p32_sf2_preset_merge_audit.py "C:\path\my-bank.sf2" --program 0 --program 7 --key 48 --velocity 100
python tools/p32_sf2_preset_merge_audit.py --self-test
```

## Release gate

1. **Do not silently revert P26 or claim it 1:1.** Fill-only would reintroduce the original ~100 ms delay and change chorus, Q and attacks. Spec addition may be correct for an SF2 2.01 VxD; source evidence is not sufficient to settle this.
2. Obtain the actual original **Win95 VxD** note-on trace for these very presets in a validated guest (not the current broken P31 DOS SDK). Compare `CCCA/IP/ENVVOL/ATKHLDV/IFATN/CSL` using `sources/tests/notes_diff.py`. A one-byte SF2 version change is only a format gate, not a parity test.
3. Only after **register evidence** proves a specific rule should we change the plugin. Capture both alternate outcomes in regression tests and document the driver family.

**Decision:** Keep stable P26; do not change original chip, SF2 samples, or filters based on unsupported guesses. Technical discrepancy found; authenticity test is still open.
