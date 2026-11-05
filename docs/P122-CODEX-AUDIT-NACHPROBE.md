# P122 Codex audit – corrected code and follow-up tests

Status: 2026-11-05. This is a remediation record, **not** an independent Codex re-audit or release approval.

- Audited original HEAD: `4c465001214d8a47b945fc734a46f776d8fb4473`
- Corrected and validated HEAD: `d8b0af795dddd86594ef7076b061f75b65340fee`
- Windows Actions: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42035683374
- Result: **34/34 CTests, 47/47 Steinberg VST3 Validator, 3/3 EditorHost PASS**.
- Active branch: `fix/p122-bank-dirty-audit`. No new branches created.

## Five reported findings and their corrections

1. **High / zero-sample pitchbend:** `src/vst3/Factory.cpp` now explicitly commits pitchbend from legal zero-sample parameter flushes. Production helper `src/vst3/PitchZeroFlush.h` takes the *last* valid frame-zero point per MIDI channel. Regression: `tests/p120_midi_automation.cpp` (same helper as actual processor). Tests do not claim acoustic reference-hardware parity.
2. **High / RPN range retuning:** `src/engine/Synth.cpp` refreshes allocated playing voices immediately when CC6 changes RPN 0,0 range; unchanged automated bend no longer blocks the necessary update. Regression: `tests/p121_pitchbend_audio.cpp` synthetic-ROM backed PCM test.
3. **High / unrelated-channel pan drift:** `Synth::RenderBlock` now schedules Win95 pan steps by the actual 227-chip-frame interval, independent of host call size. Regression: `tests/p121_pitchbend_audio.cpp` whole-block vs one-frame PCM equality.
4. **High / torn getState programs:** `src/vst3/Factory.cpp` brackets RT processing and control-thread state recall with independent atomic generations; getState retries to obtain a coherent program/bank/mask/channel snapshot rather than saving mixed data. Helpers: `src/vst3/RealtimeStateVersion.h`. Regressions: `tests/p122_rt_state_snapshot.cpp` and concurrent program queue + getState in **real exported plugin** `tests/p122_vst3_bank_host.cpp`.
5. **Medium / failed browser-bank message:** `src/vst3/PresetBrowserView.cpp` now declines the selection and shows an explicit error if the required same-value reselect message cannot reach the processor. No separate automated mouse-click simulation of this failure is claimed.

## Remaining independent acceptance

- Run a fresh Codex code review against `d8b0af795dddd86594ef7076b061f75b65340fee`, not the prior 4c46500 commit. The previous five findings should be re-reproduced, and the fixes audited for regressions.
- Release still requires the original-ROM/SBK/SF2 audio and target-DAW acceptance work. No original or private audio assets belong in this public repository or its CI logs.
- GUI development is distinct from release approval. No GUI code was altered in this correction series.
