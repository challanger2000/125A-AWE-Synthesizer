# Audit patch AWE-P01/P02/P03 — engine safety candidate

**Status: candidate, Windows tests NOT RUN until CI results verified.**
Baseline upstream: `turican0/AWE32Emu@17b0578fe59909dfaa784b5531d6d1a3a80729ce`.
Original source remains unchanged under `upstream/AWE32Emu/`.

## Implemented candidate changes
- The active adapter is isolated in `src/engine/` and uses the same EMU8000 rendering functions.
- ROM reading moved to the non-realtime `Emu8000Box::Init`, passed as instance-specific bytes to the C engine. Missing, truncated or unreadable images return errors; no `fatal` or `exit` anywhere in the patched init path.
- The C EMU8000 renderer now uses `emu8k->target_pos` rather than process-global `wavetable_pos_global`. 980-frame block timing and existing register write scheduling are retained.
- The 86Box wrapper queues and FIFO have compile-time fixed storage, eliminating its own `push_back` and `fifo.assign` allocations on audio. At 32768 queued register writes per 980 frames, it deterministically fails closed to silence until reinitialized, rather than continuing with partially applied voice state.
- Partial initializations are cleaned up, including the otherwise leaked `empty` chip buffer. Native C engine returns status rather than abruptly terminating the host.

## Scope boundaries — release blockers remain
1. **Not all of the synthesizer is realtime-safe.** Upstream `Synth::NoteOn`/`StartLayers`, `SoundFont::Bank::Select`, and `Emu8000Core::RenderNative` still allocate using vectors; these need separate bounded, tested changes.
2. Shared static chip lookup tables may be rewritten on later instance initialization. Concurrent init/playback needs source-level isolation and ThreadSanitizer/Windows stress proof. Two sequential instances alone do NOT prove thread safety.
3. 44.1kHz fixed chip engine and 980-frame internal delay still need correct sample-rate conversion and VST3 latency reporting.
4. No VST3 Processor/Controller, project asset recall, SF1/SF2 ROM backed playback, hardware audio matching, GUI or DAW verification in this change.
5. Synthetic ROM used by the tests is generated in the test's temporary directory, **not copyrighted sound data** and not a timbral/accuracy oracle.
6. The 32768-write capacity is a provisional protective bound, **not** a proven worst-case maximum; test real worst-case register counts and define a legitimate overflow-recovery policy before release.

## Test intentions
Native test verifies missing and truncated ROM handling, two independently allocated chip instances, initial 980-frame silence, pathological queued writes and no-process-exit failure policy.

**Evidence status:** pending Windows compile and CTest. No validator or Studio One test has run.
