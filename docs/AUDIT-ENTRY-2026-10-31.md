# 125A AWE Synthesizer — initial upstream code audit and test adequacy map

Status: **SOURCE INSPECTION ONLY — implementation / Windows CI / ROM-backed tests NOT RUN**. These are test hypotheses and directly observable source hazards, not claims of measured failures in Studio One.

Source baseline: `turican0/AWE32Emu@17b0578fe59909dfaa784b5531d6d1a3a80729ce`.

## High-priority findings before VST3 integration

| ID | Source evidence | Risk | Required proof / correction |
| --- | --- | --- | --- |
| AWE-P01 | `Emu8000Box.cpp`: `fatal(...)` calls `std::exit(1)` | Plugin failure could terminate DAW process | Replace fatal process-exit path with error propagation/instance-local safe silence, test failure injection inside packaged VST3 |
| AWE-P02 | `Emu8000Box.cpp`: `g_romPath`, `wavetable_pos_global`, `music_pos_global` | Global instance-state can couple two instances and different ROM paths | Isolate/serialize chip state correctly; run two concurrent instances with independent ROM/parameters; check data race |
| AWE-P03 | `Emu8000Box::PortWrite` uses `pending.push_back`; `FlushBlock` uses `fifo.assign` on rendering path | Heap allocation may occur in audio callback | Preallocated bounded queues/ring storage and sample buffers, instrument new/delete and run hostile polyphony/event saturation |
| AWE-P04 | `Emu8000Box.h`: `kBlockFrames=980`, `kLatencyFrames=980`; `RenderFrame` expects 44.1 kHz | 22.222... ms engine pipeline latency at 44.1k; host rates differ | Explicit callback adaptation, constant-latency accounting, host PDC reporting and resampling; test 44.1,48,88.2,96,192 kHz and unusual rates |
| AWE-P05 | CLI-oriented `main.cpp`, `Sequencer.cpp`, `Synth.cpp` with no VST3 factory/processor/controller | No playable MIDI instrument is delivered by source import | Implement VST3 event/MIDI conversion with sample offsets; transport/cycle; program bank/CC/RPN/NRPN, note-off/panic, 16 channels |
| AWE-P06 | `Synth::LoadWaveRom`, `Synth::LoadBank`; external ROM/SF1/SF2 dependencies | Missing/corrupt/unavailable resource may change sound, crash or break recall | Bounded file parser, resource validation on non-audio thread, atomic load/rollback; save/reload project and test missing assets |
| AWE-P07 | Optional `--chip ours` and `--chip 86box`; multiple driver variants | Silent change of emulation family may alter original sound | Pin default chip + driver variant; identical register traces/golden PCM to baseline; document intentional deviations |
| AWE-P08 | 86Box GPL-2.0-or-later and undecided upstream non-86Box license | Public binary and source distribution may require GPL-compatible permissions and complete source | Record grant terms and audit all transitive dependencies before release |

## Mandatory 125A requirement-to-test gate

For each ID above: record expected behaviour, positive test, negative/failure test, boundary test, sample-rate/block-size matrix, test fixture, exact commit/build environment, observed audio/MIDI/host state, and status **PASS / FAIL / NOT RUN**. Green compilations do not replace full-chain tests.

**Next implementation order:** (1) frozen repeatable baseline CLI/audio checks; (2) asset and multi-instance lifecycle failure tests; (3) bounded, allocation-free realtime chip adapter; (4) sample rate/latency bridge; (5) native Steinberg SDK 3.8.1 VST3 Processor/Controller C++23; (6) actual VST3 packaged-host MIDI/audio/recall/GUI and Studio One proof.

**Windows Release / Studio One / official Steinberg Validator / 125A Plugin Tester:** NOT RUN.
