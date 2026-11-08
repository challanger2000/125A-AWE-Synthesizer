# P184 – P182 real ASIO reference–AWE–reference result (8 November 2026)

## Source and status

The owner supplied the original local ZIP
`P182-LOCAL-RESULT-20261108-221242-090ab1f8.zip`.
Its `P182-COMPARISON.json` reports:
- `status=THREE_REAL_ASIO_SESSIONS_VERIFIED_DIAGNOSTIC_ONLY`
- `classification=REFERENCE_AND_AWE_GAPS_NON_EXCLUSIVE`
- `errors=[]`
- Three sequential, separately nonce-bound IASIO stream runs:
  `REFERENCE-A → AWE → REFERENCE-B`.
- Same registered **Yamaha Steinberg USB ASIO** driver,
  CLSID `{CB7F9FFD-A33B-48B2-8BC0-437D94F37142}`,
  physical driver-selected **44,100 Hz / 512 frames** (11.60998 ms per buffer).
- Same executor SHA256 for all three stages, different SHA256 for
  independently source-built MIDI-sine reference and real P178 AWE DLL;
  the two references use the **same** reference product hash.
- `physical_asio_verified=false`, `daw_session_verified=false`,
  `analog_hardware_output_verified=false`, `release_approved=false`.

## Actual three-way measurements

| Metric | REFERENCE-A (simple MIDI sine) | AWE (real original-media VST3) | REFERENCE-B (same simple MIDI sine) |
|---|---:|---:|---:|
| Actual IASIO callbacks | 1,000 | 1,000 | 1,000 |
| Successful VST3 process callbacks | 1,000 | 1,000 | 1,000 |
| Callback start interval violations | **1** | **1** | **1** |
| Violation index, zero based | **2** | **2** | **2** |
| Interval between callback 1 and 2 starts | **58.4385 ms** | **63.1304 ms** | **56.3673 ms** |
| Callback 2 relative to first start | 70.0792 ms | 75.5223 ms | 67.6881 ms |
| Previous callback execution duration | 0.0770 ms | 4.2183 ms | 0.0335 ms |
| Callback 2 execution duration | 0.0524 ms | 4.2154 ms | 0.0105 ms |
| Maximum execution duration (whole run) | **0.0916 ms** | **5.9249 ms** | **0.0967 ms** |
| Over-budget execution callbacks | 0 | 0 | 0 |
| Reported ASIO overload/resync callbacks | 0 | 0 | 0 |
| MIDI NoteOn / NoteOff | 12 / 12 | 12 / 12 | 12 / 12 |
| Nonzero internally rendered PCM samples | 528,144 | 1,019,251 | 528,144 |
| Strict existing physical-ASIO real-time gate | **NO-GO** | **NO-GO** | **NO-GO** |

Each raw `ASIO-CALLBACK-TIMING-TRACE.json` reported
`trace_complete=true`, 1,000/1,000 recorded slots,
0 unrecorded slots and 0 overflows, **one** marked gap,
and seven preserved neighboring callback entries (0 through 6).
For every stage the callback worker thread ID was unchanged
throughout the preserved interval, driver buffer indices alternated
0/1, and driver overload/resync and sample-rate-change message counters
remained 0. The note-on count in the preserved window stayed 1
and note-off 0: the anomalous callback did **not** coincide
with a new MIDI note.

## Technical assessment

**Decisive controlled observation:** The independent reference
instrument has *no* AWE/EMU8000/ROM/SF2 signal-processing path and
uses at most about **0.1 ms** of CPU callback time. Nonetheless,
under the same real registered driver, hardware, ASIO host,
buffer size, sample rate, MIDI note and three separate starts,
it produced a long **third-callback start gap in both reference runs**,
bracketing the AWE run. Therefore, it is **not supportable**
to diagnose this phenomenon as an exclusively AWE-DSP-created
callback gap or to rewrite the AWE audio engine to "fix" it.
The common start-of-stream path is implicated. **No evidence here
distinguishes Windows scheduler/DPC, USB link, Yamaha/Steinberg
ASIO driver behavior, hardware firmware, or native host startup**.
A constant worker thread ID excludes an *observed thread-ID switch*
in the captured window but does not rule out scheduler preemption.
No overload message excludes an *ASIO-reported* overload,
not the physical possibility of missed audible audio.

In this controlled three-run comparison the existing
**2×buffer-time inter-start threshold** was exceeded exactly once
per run at zero-based callback index 2, and the remaining 997
indices were **not flagged by that threshold**. This is *not*
an independent DAW or hardware-loopback certification.
No source code should silently discard early callbacks,
alter thresholds, or convert these three original NO-GO
results into a physical ASIO PASS. Instead, **record cold-start
and steady-state outcomes separately in any future new test
methodology**, preserving the original strict full-run gate.

## Engineering decision and remaining release blockers

1. **Stop modifying the AWE DSP based on this single early-start gap.**
   The independent source-built sine test reproduces it twice.
2. **Do not ask for repeat identical P179/P181/P182 test cycles.**
   A new local run should answer a *new* causal question.
3. If attribution is required, a purpose-built Windows
   kernel ETW/DPC + physical IASIO startup trace with matching
   synchronized timestamps is next, or a second genuinely
   different physical ASIO interface as a separate control.
   Neither is supplied or certified by these uploaded files.
4. Preserve strict no-release state until actual DAW integration,
   analog/S/PDIF audio capture, EMU8000 fidelity comparison,
   outstanding independent FULL AUDIT and release requirements.
5. Original ROM/SF2 stay local and were **not** committed.
   This report uses only source-derived aggregate diagnostic data.

**No code change, no merge and no release authorization follows
from this diagnostic result.**
