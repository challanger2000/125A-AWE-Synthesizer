# P229 — Dry clipping root-cause: actual owner-four-bank EMU8000 signed32 measurements

**Evidence date:** 2026-11-10. **Target:** `qa/p229-dry-preclip-rootcause` derived from `qa/p228-crossbank-real-dry-audio`.

## Decision: preserve the synthesizer's production sound path

P228 rendered all 3,082 actual native EMU8000 two-second notes from the owner's four original SF2s (376 presets). All notes sounded, no GUI-0% send register leakage; **117/3,082** cases reached signed16 rails with both Reverb/Chorus set to 0%. All 117 had velocity112; none occurred at velocity48. Four original SF2s, ROM and rendered PCM were **not uploaded** to GitHub.

P229 isolates **every one** of those 117 dry rail cases at exactly the P228 note/program/bank/velocity, plus the same 117 cases with velocity48. The actual native 86Box-derived EMU8000 chip signed32 stream was captured **before the int16 clamp**, with a caller-owned preallocated buffer; the real production chip output and SF2/DSP logic were **not changed**.

## Executed source checks, not just CI

- Public, asset-free native C++23 preclip test executable: compiled and synthetic-parser/negative test **SUCCESS**, [GitHub Actions #42804304026](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42804304026), source SHA `66bc087bd10b9b6a5b1bacb56f77ce5aa56dd5d7` for diagnostic source. Real owner media run was performed **offline, not on public CI**.
- **234/234 real user SF2 audio cases rendered**, 88,200 frames at 44.1kHz stereo per case = **41,277,600 actual native stereo sample values**. The emitted real int16 PCM exactly equals `clamp(actual signed32)` for **every sample, zero mismatches**.
- **12,328 true raw32 values** outside signed16 limits. There were 12,332 exact signed16 rail values: the four-value difference is caused by samples *exactly at* the rail, not above it.
- **117/117 high velocity 112 cases** have true overrange; **0/117 matched velocity 48 cases**. Raw RMS high/low median difference **+15.117dB**. Max true signed32 peak **+5.822dBFS**.
- All 117 clipping notes **actually started 2–8 physical EMU8000 chip voices**, confirmed by `Emu8000Core::IsVoiceActive` on the actual chip. Independent original SF2 region parsing confirms the identical 2–8 eligible sample layers for each note. Thus this is a genuine many-sample-layer summation scenario, not an invented mono-note screenshot.
- All **234/234 dry cases** had *actual active chip voices* but zero `PTRX` reverb and zero `CSL` chorus send bytes. For each of the **four original user SF2s**, a separately executed 100%-FX **positive witness** detected nonzero chip send registers on 2/2/3/4 respectively active chip voices. A vacuous test checking only free voices is therefore ruled out.
- Original bank names are retained only as test identifiers; no original SoundFont, Wave ROM, PCM, guest OS, Creative driver or proprietary hardware byte material is committed or included in GitHub Actions artifacts.

| Original SF2 | Clipped note cases (vel112) | Real signed32 overrange values | signed16 rail values | Max preclip |
|---|---:|---:|---:|---:|
| Synth 512 Bank | 28 | 2,168 | 2,169 | +4.770 dBFS |
| FM Dreams Sampler | 5 | 92 | 92 | +1.543 dBFS |
| Vintage Dreams Bank | 52 | 7,691 | 7,694 | +5.129 dBFS |
| Vintage Synth 2001 | 32 | 2,377 | 2,377 | +5.822 dBFS |
| **Total** | **117** | **12,328** | **12,332** | **+5.822 dBFS** |

## One visible high-gain, multi-layer scenario

`Vintage Dreams Bank.sf2`, preset 110 `Heavy Square`, note99, velocity112: **3** sample layers actually active, comprising one high-amplitude Square wave and two Saw layers. Original SF2 sample peak magnitudes are **32767** and **32687** counts respectively. Original native chip signed32 **minimum -57,264**, maximum **+41,428**, after which the signed16 PCM necessarily clips; **2,501** PCM samples reach the limits. The layer count is measured from the active chip and independently matched to original SF2 zones.

This establishes a *plausible physical mechanism* of summed loud voices under hard attack. It does **not** establish whether the **original Creative Win95 driver/physical AWE64** would produce exactly the same combined gain or whether our velocity/sample attenuation mapping contains an offset. Generic post gain, limiter, DC removal and reducing V112 relative to original are all **unjustified** on this evidence alone.

## Real release gates

1. **Still required:** reproduce P229's exact same original bank/note/velocity (with identical CC7/11 and FX off) on the **original Creative Win95 driver**, independently verify that full original bank is loaded into 86Box's sample RAM, then capture the original chip wavetable audio and voice register history. P227's publicly authenticated SoundFont CC-sweep is a *different reference bank*, not a substitute.
2. **Still required:** exported Windows 64-bit VST3 with all four owner banks in Studio One / ASIO host; P228/P229 only establish genuine native chip audio.
3. **Still required:** independent P75/P87/P89/P97 and Test Lab audits, parameter and state recall, multi-layer loop/ADSR/filter/parity checks, original hardware as available.
4. The fourth bank `Vintage Synth 2001` targets later E-MU hardware; it is valuable for SF2 robustness but not inherently a physical AWE32 acoustic oracle.

**Status: RESEARCH POSITIVE / SOUNDFONT CLIPPING HISTORICAL PARITY OPEN / AUDIO DSP UNCHANGED / NO MERGE / RELEASE BLOCKED.**
