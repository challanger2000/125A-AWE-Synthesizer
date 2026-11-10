> **CI VERIFIED:** [P213 source-derived 42-case audit #42734359204](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42734359204) – SUCCESS at commit `8aae8d8b4560d28c9cca4f6fbf6e359006e9c5a0`. Replays frozen independent source-driver measurements (P210 14/14, P212 28/28, 31 distinct values) against the VXD signed integer conversion plus the actual additive preset-stage structure. Still research-only; no new original driver run or full call-graph proof in this step.

---

# P213 – Exact original Creative VXD arithmetic and source-preserving SF2 preset staging

**Evidence status: original numeric driver measurements independently replayed against source-derived arithmetic. Product unchanged.** This report supersedes the unconfirmed P211 126-scale ties-to-even research guess; do not change original measurement fixtures to fit a model.

## Original vendor source identity
- Original Creative Win95 `SBAWE.VXD`, 77,370 bytes, SHA-256 `d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a`, was verified in the P212 test guest, then downloaded and hash-checked again for private disassembly under `125A-Engineering`.
- The correct, tested 1998 VxD is **LE** (32-bit Linear Executable). **Important adversarial fix:** LE page map uses a *big-endian 24-bit page number*; the initial P213 decoder incorrectly parsed it as little-endian and showed nearly empty code. Corrected with a nonzero source-code gate and independent synthetic LE test.
- Validated [P213 original-driver static-analysis CI](https://github.com/challanger2000/125A-Engineering/actions/runs/42733401691).
- The original driver contains, in executable object `LE.object4` near offsets `0x3A33..0x3A44`, integer operations equivalent to `127 + signed-trunc-toward-zero((-127 * x) / 1000)`: multiply by negative 127, x86 `CDQ; IDIV 1000`, add 127. This is a factual property of those assembly instructions; this record does not redistribute driver code.

## Why P211 appeared to work but P212 disproved it

The P210 and P212 SF2 test banks are not direct, independently generated instrument Sustain banks. They clone a **Creative-accepted public SoundFont** with an original instrument `sustainModEnv=500` on sample 43. Appended preset generator amounts are **additive deltas** `requested - 500`. The generator is not replaced or reset to zero at the original instrument. See `tools/p210_clone_verified_sf2.py`, `tools/p212_clone_sf2.py`.

The source-derived model for **this specific fixture** is:

`T(x) = 127 + trunc_toward_zero((-127*x)/1000)`

`DCYSUS_high = T(500) + T(requested-500) - 127`

This is not the same as applying one rounded scale to the final merged value. Examples: `requested=249` yields `T(500)=64`, `T(-251)=158`, hence **95**. `requested=625` yields `64 + T(125)-127 = 49`. `requested=1000` yields `64 + T(500)-127 = 1`. These cases were among the discrepancies that disprove the one-stage 126-scale hypothesis.

P210 supplied 14 separately captured original-driver register cases (seven different values), P212 supplied 28 further original-driver register cases (24 new values and 4 repeated controls). Together they comprise **42 note-case measurements and 31 distinct Sustain inputs**. Frozen numerical original-register fixtures and mutation tests are committed separately; no original binaries/ROMs/SF2 media are distributed here.

## Verification discipline and limits

- A new automated, independent source-derived test compares the frozen 14 and 28 genuine original Creative observations, using signed integer truncation and the source-preserving preset deltas. Its own GitHub Actions result is the authoritative status. A mathematical PASS must never be called a new original driver measurement.
- Still **NOT PROVEN**: an instruction-level *call graph* from SoundFont generator 29 to this exact VxD conversion branch, complete behavior with *different instrument-base Sustain values*, physical EMU8000 output and all DAW/ASIO VST3 usage.
- No product DSP, preset mapping, VST3, hardware ROM or shipping branch is modified. No FULL AUDIT, no release, no unreviewed merge.
- Next source-directed discriminator is an independent original-driver experiment varying both instrument-level and preset-level Sustain while preserving authentic sample payload and observing the real register writes; do not extrapolate the base-500 result to arbitrary SF2 banks without this evidence.
