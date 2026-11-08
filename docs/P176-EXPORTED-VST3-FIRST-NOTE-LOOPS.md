# P176 — exported Windows VST3 first-note and SF2 loop semantics

**Candidate source:** P175 `3203fe8df1531c29a9ea944e1ce9d05af74d1769`.
**Branch:** `qa/p176-exported-vst3-first-note-loops`.
**Status at authoring:** CODE/TESTS ADDED; Windows execution **NOT RUN** until corresponding GitHub Actions job actually finishes. Not a FULL AUDIT or release.

## Independent audit finding: previous first-note test is not the full GUI path

Existing `tests/p171_vst3_load_host.cpp` loads the actual exported product DLL,
but sends `125A_SF2_LOAD` **directly to the Processor connection**, rather than
calling `Controller::RequestSf2Load` through the user's VSTGUI/Windows
file-selection flow and then selecting an SF2 preset in `PresetBrowserView`.
It measures the first NoteOn after a completed synchronous load, **not** the
full UI request/ACK/catalog-refresh/host-parameter-queue sequence. The P171
9/9 first-note checks must not be described as a reproduced fix of the
owner's first-click symptom.

The user SF2/ROM original local native P174 exercises did not reproduce the
first-note failure after a completely loaded native Synth, but also cannot
prove that the full VST3 controller/UI lifecycle works in the owner DAW.

## Added actual product-DLL loop tests

- Reuse the public analytical SF2 generator already independently validated
  under P170; generate three independent loop-mode fixtures in the **external
  test temporary directory**. Each has a distinct RIFF `sampleModes`
  value: 0 (one shot), 1 (continuous), or 3 (until release). LoopEnd=4080,
  End=4096, **16 sample words of release tail**.
- Load these into actual Windows x64 **exported DLL**, not only a stand-alone
  native Synth or extracted Processor. In each fixture render the first MIDI
  NoteOn immediately after the accepted SF2-load message.
- Send NoteOff at exactly 1.0 seconds using the VST3 event sampleOffset.
  Test independently at 44100, 48000 and 96000 Hz, 1024-sample blocks.
- Check first-note **nonzero PCM**, held-note RMS, post-NoteOff RMS and
  byte-for-byte equality against an otherwise identical fresh DLL instance
  preloaded with the same SF2.
- One-shot must have stopped by 0.3s, continuous mode must hold before and
  after release, mode 3 must hold before NoteOff and end quickly after
  release. These independent audible assertions reject a common
  always-loop or always-stop mutant even if the two product instances agree.
- Keep all nine original P171 DLL-first-note fixtures and the complete
  Windows CTest/validator/EditorHost/GUI/Test-Lab regression in the one
  scoped P176 CI run; no productive Synth, EMU8000, GUI, ParamID, or state
  changes made.

## Coverage boundaries (deliberate NO-GO)

| Contract | Gate |
|---|---|
| Actual exported DLL immediate note after **direct Processor load** | P171, existing nine tests; no claim about Controller dialog |
| Actual exported DLL 0/1/3 loop acoustic windows | P176 new nine cases — **NOT RUN** until CI |
| Original private SF2 loop-specific presets and creative hardware | **NOT VERIFIED** |
| Controller RequestSf2Load → ACK → CatalogRevision → browser Select → host parameter queue → first PCM | **NOT VERIFIED**; requires additional real-UI/host instrumentation |
| Actual DAW Studio One / ASIO / MMCSS realtime | **NOT RUN** |
| P170/P171 1/28,800 RT deadline overrun | **formal FAIL remains**, unchanged |
| FULL AUDIT, commercial release, branch integration | **NO-GO** |

Do not repair a suspected loader timing issue without an actual failing end-to-end
PCM reproduction and a pre-fix negative control. No private ROM/SF2 or
copyrighted source audio in any CI fixture or Git commit.
