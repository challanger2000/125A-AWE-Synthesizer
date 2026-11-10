# P212 – Independent original Creative Win95 EG1 Sustain sweep (research only)

## Purpose
Test the P211 hypothesis against **new original driver observations**, not another mathematical replay of P210. No source-DSP change, no VST3 release, and no assertion of physical EMU8000 hardware parity.

## Frozen input domain (before the original Win95 test)
28 MIDI programs 100..127 in SF2 bank 0, auditioned in the original Creative User Bank 1 at MIDI note 59, velocity 100. Their sustainModEnv values in order:

0, 1, 3, 4, 7, 8, 11, 12, 19, 20, 31, 32, 63, 124, 125, 249, 250, 251, 375, 376, 624, 625, 749, 750, 751, 875, 993, 1000.

Four fresh-execution **repeat controls** (0, 250, 750, 1000) must reproduce the corresponding P210 high bytes (127, 95, 33, 1). The remaining **24 distinct values were not tested in P210**. HoldModEnv stays at 0 in all 28 programs. P210's 14 note cases contain only seven distinct Sustain values and cannot establish a full transfer law.

## Independent evidence chain
1. Source: authenticated public original SoundFont Spec Test SF2, Git blob 4768c4a0215abf49c7a2bb51ada5ba3494faa1c5, already accepted by Creative. Append 28 presets only. Preserve all 44 samples, 25 instruments and original six presets. A fresh SHA-256 ties the derived SF2 to the checked manifest.
2. Guest: an actually booted, ephemeral Windows 95 installation, original Creative SBAWE.VXD and WinMM, 86Box emulating the AWE64 Gold with 28 MiB sample RAM. Ensure the original driver receives all 28 programs and notes through the guest UART. Verify original-bank upload activity and nonzero EMU8000 PCM, not merely UI status.
3. Trace: capture **28 isolated, ordered native original-driver register windows**, require one distinct EMU voice per window, one ATKHLD and two DCYSUS writes, and extract the first DCYSUS high byte. Four historical control bytes must repeat unchanged or the comparison is invalid.
4. Compare after capture: check the P211 integer formula 127 - round-ties-to-even(126 * sustain / 1000) against all observed high bytes, and report 127-truncation, 127-half-up and 126-half-up alternatives. Ten source/provenance/window mutations must fail.
5. Keep discrepancies. CI can succeed if authentic original-driver evidence falsifies P211: a bad scientific hypothesis is **not** a successful prediction, but should not be overwritten to manufacture a perfect score.

## Boundaries
A matched 28/28 would support the proposed formula over 28 observed integer settings only; it cannot prove the entire integer interval 0..1000, revision equivalence, the original VXD arithmetic or physical silicon. A full sweep, reverse engineering of the VXD path and genuine hardware audio references remain separate work. The known 81.85-cent attack pitch discrepancy and studio/ASIO tests are not addressed here.

## Status
- Source generators and original-driver runner: research implementation, pending CI execution.
- New original Creative measurements: **NOT RUN** until a linkable P212 workflow run and artifact show otherwise.
- Product DSP/VST3: unchanged. FULL AUDIT / DAW / ASIO / release: **NOT RUN / NO-GO**.

Related: [P210 actual original-driver run](https://github.com/challanger2000/125A-Engineering/actions/runs/42722686808) and [P211 independent mathematical audit](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42725463629).
