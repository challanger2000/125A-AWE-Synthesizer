# P228 – Four real owner SoundFonts: native EMU8000 dry PCM audit

**Status:** Actual Linux-x64 native 86Box-derived EMU8000 audio runs completed locally on the four original user-provided SF2 files and owner original 1-MiB wave ROM. No private media in GitHub. **No VST3/Studio One/physical Creative sound-fidelity claim; release BLOCKED.**

## Test implementation / build

- Source baseline: this unmerged P226 diagnostic branch, with `tools/p228_batch_dry_native.cpp` and strict isolated SF2/program selection.
- [Actual Linux compilation and parser-negative-mutant CI](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42799468054): SUCCESS, commit `eacd09cbbaddaeaffa6d0d840782d967ed848a2c`, self-contained Linux x64 native EMU8000 binary artifact.
- Initial false failure: CSV has Windows CRLF line endings; fixed parser before actual owner execution. The earlier binary was NOT accepted as a dry-audio PASS.
- **Every note trial created a fresh standalone chip and loaded only its own SF2** with strict no-ROM/GM-fallback program selection, 44.1kHz signed16 stereo 2 seconds per note, NoteOff after 1 second; user SF2 files and ROM never entered public CI. No normalisation or audio modifications.
- GUI reverb = 0 and chorus = 0. To adversarially check SF2/CC override, send actual MIDI CC91=127 and CC93=127 (plus CC7=100 and CC11=127), then read active-voice PTRX and CSL effect-send bytes from the chip and record nonzero cases. A full native PCM output, active note and RMS/peak/rails were measured. This proves source-branch native-path behavior, not VST3-host serialization and automation.
- SHA256 identities for user SF2s are recorded in the owner-private local JSON only; source files remain unchanged.

## Completed actual native-audio matrix

| User original SoundFont | Presets | Actual rendered 2s notes | Missing voice | Digital silence | Nonzero FX-send cases | Dry clipping cases |
|---|---:|---:|---:|---:|---:|---:|
| Synth 512 Bank | 77 | 688 | 0 | 0 | 0 | **28** |
| FM Dreams Sampler | 35 | 210 | 0 | 0 | 0 | **5** |
| Vintage Dreams Bank | 136 | 1,272 | 0 | 0 | 0 | **52** |
| Vintage Synth 2001 | 128 | 912 | 0 | 0 | 0 | **32** |
| **Total** | **376** | **3,082** | **0** | **0** | **0** | **117** |

**Critical finding:** 117 dry cases reached the signed16 rails, total 12,332 samples. 27 cases had >100 rail samples; 1 had >1000. High-velocity examples: Vintage Dreams 'Heavy Square' bank0 program110 MIDI99/V112 had 2501 rail samples; 'Detuned Saws' program4 MIDI99/V112 715; Vintage Synth 2001 'LED:Ragged Tooth' MIDI84/V112 574. No dry FX sends were active in the recorded scenarios. **Do not call these 117 a bug in the AWE32 model until original Creative Win95 driver produces matched MIDI/FX and its audio is compared.** Avoid automatic gain compensation or limiting in the sound-fidelity engine without evidence.

**Bank consistency:** For 67 identical-name Synth512/VintageDreams presets, 622 shared note/velocity cases produced *identical all seven numerical PCM output metrics* (RMS, peak, negative and positive rails, DC, nonzero sample count, first nonzero frame) 622/622. Not a full sample-by-sample PCM-comparison and not proof of authentic original hardware sound.

**Test scope / NO-GO:** No P228 real exported Windows VST3 process, no Studio One DAW/ASIO, no matched original Win95 SBAWE.VXD bank-loaded audio, no physical CT4390, no exact loop transitions, envelope parameter sweep, or sample-exact spectral/hardware comparison in this matrix. The Vintage Synth 2001 SF2 declares a 10K1 target, so it is a compatibility test rather than independent proof of EMU8000 fidelity. Keep internal reverb/chorus default 0 independently of SF2, manual controls preserved on preset changes. Prioritize the 117 dry-peak cases for reference-driver A/B instead of further FX tuning.

**Private evidence files (not pushed):** `P228-Real-Audio-Auswertung.json`, `P228-Alle-3082-Audio-Messwerte.csv`, and `P228-Real-Audio-Bericht.md`. The public repository includes this aggregate non-media report and test tool only. No proprietary SF2s, user audio, 86Box ROM or OS image.
