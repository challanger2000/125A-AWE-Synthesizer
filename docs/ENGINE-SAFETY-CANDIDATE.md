# Audit patch AWE-P01/P02/P03 — engine safety candidate

**Status: native Windows CI PASS for P01/P02/P03, initially verified in run #41229506821; subsequently rerun in #41232207613. Still a candidate, not release-approved.**
Baseline upstream: `turican0/AWE32Emu@17b0578fe59909dfaa784b5531d6d1a3a80729ce`.
Original source remains unchanged under `upstream/AWE32Emu/`.

## Implemented candidate changes
- The active adapter is isolated in `src/engine/` and uses the same EMU8000 rendering functions.
- ROM reading moved to the non-realtime `Emu8000Box::Init`, passed as instance-specific bytes to the C engine. Missing, truncated or unreadable images return errors; no `fatal` or `exit` anywhere in the patched init path.
- The C EMU8000 renderer now uses `emu8k->target_pos` rather than process-global `wavetable_pos_global`. 980-frame block timing and existing register write scheduling are retained.
- Shared mathematical lookup tables (frequency, envelopes, LFOs, filters, cubic interpolation) are now populated only once via non-realtime `std::call_once`, with an explicit native regression count; per-instance register random state moved from a mutable global to `emu8k_t`.
- The 86Box wrapper queues and FIFO have compile-time fixed storage, eliminating its own `push_back` and `fifo.assign` allocations on audio. At 32768 queued register writes per 980 frames, it deterministically fails closed to silence until reinitialized, rather than continuing with partially applied voice state.
- Partial initializations are cleaned up, including the otherwise leaked `empty` chip buffer. Native C engine returns status rather than abruptly terminating the host.

## Scope boundaries — release blockers remain
1. **Realtime work has progressed since this patch.** The active P04/P05 files now have bounded NoteOn selection and allocation-free native RenderBlock in their tested paths. This does not establish that all MIDI/event, sample-upload or diagnostics paths are real-time safe; full audit remains required.
2. Concurrent initialization now has table immutability and bounded multi-instance native coverage, but **a full ThreadSanitizer/Windows concurrency stress test and real audible multi-instance parity still remain NOT RUN**. Other original mutable global state must be reviewed before multi-instance sign-off.
3. The active P05 native engine now has 44.1/48/96 kHz streaming SRC and converts the 980-frame internal delay to host frames. No VST3 host-latency reporting or authentic 86Box timing parity has been validated yet.
4. No VST3 Processor/Controller, project asset recall, SF1/SF2 ROM backed playback, hardware audio matching, GUI or DAW verification in this change.
5. Synthetic ROM used by the tests is generated in the test's temporary directory, **not copyrighted sound data** and not a timbral/accuracy oracle.
6. The 32768-write capacity is a provisional protective bound, **not** a proven worst-case maximum; test real worst-case register counts and define a legitimate overflow-recovery policy before release.

## Test intentions
Native test verifies missing and truncated ROM handling, two independently allocated chip instances, initial 980-frame silence, pathological queued writes and no-process-exit failure policy.

**Evidence:** Windows-2022 / MSVC 2022 completed successfully: [#41232207613](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41232207613), 5/5 native tests PASS. No VST3 validator or Studio One test has run.
