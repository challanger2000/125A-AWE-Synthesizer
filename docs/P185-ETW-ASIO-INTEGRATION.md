# P185 independent Windows ETW / ASIO integration

Task [#91](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/91).
Baseline P184 `3aaa2f736535dde3642ab7cea11d919059ff12bb`. Engineering rules at
`bc26392ec7ea9f20f074bff84bbc47ab439d5fe0` fully read, including START,
ENGINEERING-GUARDRAILS, AUDIT-COMPLETENESS-CONTRACT and local AGENTS/START.

Universal implementation and adversarial/native Windows tests live in Test Lab
branch `feature/p185-independent-etw-asio`; see its
[method and coverage](https://github.com/challanger2000/125A-Plugin-Test-Lab/blob/feature/p185-independent-etw-asio/docs/P185-INDEPENDENT-ETW-ASIO.md).
This branch changes integration/docs/workflows only. The AWE sound core, GUI,
original-media requirement, 28 MiB sample RAM limit, existing entire-run ASIO
2-buffer spacing limit, XRUN/error gates and P179–P184 evidence stay unchanged.

P184 measurements are already completed and are not repeated. P185's single
reference-only physical ASIO run is **NOT_RUN until the owner's local BAT**.
No ROM/SF2 prompts, no installer/driver changes, no manual Python. Actual ETW
capability/privilege failure is ETW_NOT_AVAILABLE; missing/lost/unbound data is
INCONCLUSIVE. No provider-name/USB temporal correlation becomes a causal claim.
Minimal P185-ACCEPTANCE.json is separate from private local raw ETL and aggregate.

New AWE Windows regression builds the unchanged production source with the pinned
SDK, runs the entire CTest suite (including actual exported-DLL PCM/negative
controls), Steinberg validation and real EditorHost smokes/GUI regression. This is
a software regression, not another P184 physical A/B/A measurement. Packaging
will reuse the proven P178 Windows binary, verifying its original manifest/source,
and link exact P185 Test Lab tooling. No release, merge or FULL AUDIT approval.

Status: Windows execution/package verification pending. All actual results and
exact final CI/source references will be recorded after execution. Physical P185
ASIO/USB root cause and target-machine realtime remain **NOT_RUN / INCONCLUSIVE**.
