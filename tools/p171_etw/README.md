# P171 — causal follow-up of the frozen final-source Windows traces

Audit-only branch `audit/p171-etw-b02e02d`; no product source modifications.
Original product/test source: `b02e02d472544eb2122533f9b8d7dc9d0b97f68a`.
The two original QA artifacts are from run 42479356487, never substituted by
a new stress run. Their published summary and raw CSV hashes are checked first.

The native decoder adapts the fully read P132 decoder from
`fca1effcc06fae4c134b8437b72fefb3638f75c9`. The target-thread CSV column is
resolved by its `tid` header; the old P132 column index is inapplicable here.
TDH supplies the actual CSwitch fields and state; raw QPC timestamps are used.
No cycle-to-time conversion and no inferred CPU frequency.

Analytic timelines deliberately challenge ready preemption, waiting, scheduled
runtime, wrong clocks, missing boundaries, lost events and failed calibration.
Two real Windows busy and two Sleep controls must then validate the decoder.
They run on the analysis runner, not retroactively inside the original trace.
For each original callback, full on/off interval coverage, zero ETW losses and
matching QPC frequency are required before a causal label can be assigned.

Scheduled time includes any executing code and interrupts; it is not pure DSP
proof. Waiting requires stack investigation before assigning a plugin lock.
GeneralProfile is not a complete heap profile. Heap/physical ASIO/DAW evidence
remains NOT RUN; no release approval. The timing executable contains the
source-identical extracted Processor; it is not the shipping DLL timing host.

The follow-up publishes the unchanged original CSV and calibrated numeric
results as SHA-256-verifiable compressed notices as well as QA artifacts.
