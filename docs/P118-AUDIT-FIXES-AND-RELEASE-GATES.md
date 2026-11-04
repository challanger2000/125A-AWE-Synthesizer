# P118 – Independent review and correction of Codex P117 audit

**Base:** `develop/p117-synthgm-recall-fix`
**Isolation branch:** `fix/p118-audit-critical`
**Scope:** Windows x64 VST3, VSTGUI, EMU8000. Never alter authentic 86Box chip register math simply to eliminate original hardware saturation.
**Source:** 2026-11-04 independent Codex audit, ten findings P117-01..P117-10.

## Implemented corrections

| Finding | Correction | Limits / remaining verification |
|---|---|---|
| P117-01 – HIGH: malformed SoundFont causes OOB | Strict RIFF/LIST data bounds, 16-deep list limit, valid RIFF/sfbk header, table-size and all bag/gen/sentinel index checks. Reject malformed files before dereference. 64 MiB input cap, guard zero-byte and odd sample chunks. | Synthetic valid/invalid parser test including hostile sample size and 65534/65535 bag indices; ASan/UBSan repeat required for final hardening. |
| P117-02 – HIGH: missing CC/pitch/pressure | Standard VST3 IMidiMapping, stable per-channel automatable parameter IDs >= 2000 for CC 0/1/6/7/10/11/32/64/91/93/100/101/120/121/123, channel aftertouch 128, pitch bend 129; events forwarded to actual `Synth` functions. | No Studio One MIDI keyboard capture with CC64/pitch/aftertouch yet. `kIsHidden` intentionally NOT used, because the Steinberg SDK forbids external edits on hidden parameters. |
| P117-03 – HIGH: try-lock drops notes/events | Remove early-return `try_to_lock`. Audio processing serializes with host state swaps. Project stream I/O and ROM/SF2 preparation occur outside `engineMutex_` in getState, setState, setActive, and notify. | Locks can still briefly block RT on a genuine engine swap. No release-level deadline/WCET measurement yet. No claim of lock-free DSP. |
| P117-04 – HIGH: active recall UI/audio divergence | `Processor::setState` parses full candidate and prepares ROM+SF2+GM off-lock. Publish new `state_`, engine and load flags together only after successful preparation; explicit missing ROM silences old engine. Reject invalid assets without replacing working state. Preserve V1–V9 state format. | Original-ROM/SBK host active recall with two real banks requires Studio One integration fixture; serialization tests alone are insufficient. |
| P117-05 – HIGH: stale asynchronous bank snapshot | `assetGeneration_` rejects prepared ROM/SF2 loads superseded by another activation, recall or asset commit. Live bank, program and overlays applied at commit from current host state. | Concurrent host/automation integration test pending, including rapid repeated selections and plugin removal. |
| P117-06 – MED: automation applied at block start | No longer only use last point per parameter queue. A preallocated array of up to 1024 queue cursors merges all parameter sample offsets with incoming note events and segments renderer without allocating. | Actual cross-block-size PCM equivalence on host automation still pending. |
| P117-07 – MED: wrong Ctrl-click defaults | Twelve overlays explicitly reset to 0%, master volume to 100%, with explicit custom VSTGUI Ctrl-click handling rather than inherited ambiguity. | Real EditorHost Ctrl-click mouse check added. |
| P117-08 – MED: missing host latency notification | Hardware readiness status detects ROM absent↔loaded and queues `restartComponent(kLatencyChanged)` from UI idle, not the connection/audio thread. | UI must be open for this callback; host-closed-editor latency transition needs separate solution. |
| P117-09 – MED: asset changes not dirty | On acknowledged ROM/SF2 file change, call `setDirty(true)` on editor UI thread; optional IComponentHandler2 may reject. | Confirm actual project-save indicator in target DAW. |
| P117-10 – LOW: stale browser highlight | `Select` synchronizes row highlight and direct selectors for PREV/NEXT/browser/host parameter changes without recursion via syncing guard. | End-to-end keyboard navigation in Studio One pending. |

## Critical integration boundaries

- All ten source paths were inspected. Code changes in this branch have to be distinguished from release-level proof; no original proprietary Creative data in CI or packages.
- The new MIDI mapping introduces host parameters that are not on the faceplate. It keeps previous VST3 parameter IDs intact.
- `kLatencyChanged` currently relies on the open editor's idle refresh path. It is not valid to claim a host-wide latency correction with the editor closed.
- `engineMutex_` is still used on the audio callback; the priority of this change is **never lose a NoteOff or automation event**. The cost must be measured under actual Studio One load before release.
- VST3 host state migration V1–V9 remains unchanged; no new persisted data added.
- Black/gold faceplate redesign remains **on hold** pending host-level testing.

## Tests

- `tests/p118_soundfont_parser_bounds.cpp`: real production loader with a valid synthetic SoundFont and malformed bag, truncated RIFF and inflated sample chunks.
- `tests/p118_midi_mapping.cpp`: 16-channel mapping, stable parameter IDs, CC/pitch values and defaults.
- `tests/p14_vstgui_contract.py`: new integration contract for IMidiMapping, sampleOffset and lossless process locking.
- `tools/p18_editorhost_smoke.py`: real Win32 GUI screenshot, drag/Reset, new Ctrl-click neutral/unity verification; no original ROM data.
- `tests/sf2_audio_integration.cpp` and GUI fixture corrected: synthetic EOS `shdr` must be **46 bytes**, not 50; strict parser revealed preexisting invalid test fixtures.

## Release decision

**Not yet a final release.** A successful VST3 validator and green CI do not substitute for original-ROM/SBK SF1 playback, sample-accurate CC/automation and active project-state recall with the actual DAW. P118 remains isolated from P116/P117 release until verified.

Recommended next gate: P118 Windows CI complete -> inspect actual Win32 GUI screenshots and test report -> Studio One with original `awe32.raw` and `SYNTHGM.SBK`, keyboard sustain/pitch bend, two bank recall cycles, live load/automation concurrency and CPU glitch monitoring -> independent Codex follow-up read-only audit.
