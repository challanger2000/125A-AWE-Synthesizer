# P205 – EG1 pitch-domain inverse audit: CT4390 Hz vs cents, P203 falsification

**Date:** 2026-11-09. **Scope:** research-only. **Production VST3 audio code unchanged.** This is an offline reanalysis of existing, SHA-pinned physical AWE64 Gold CT4390 comparison metrics. No hardware was newly measured, no SoundFont/ROM/audio was committed, and the experimental P203 DSP must **not** be promoted to product.

## Original sources, reproducible inputs and controls

- Baseline original [full CT4390 P193 comparison #42685155427](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42685155427), archive artifact `13703694431`, P200 original measured bins.
- Experimental slow-only P203 original [CT4390 full comparison #42685310513](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42685310513), artifact `13705190866`, P200 measured bins. Both completed **SUCCESS** on the original audio tests. CI success alone is not chip-fidelity proof.
- Original SF2 test v3.0 note 59, bank 0/program 0, **one** instrument zone, sampleID 43; `modEnvToPitch=+1200 cents`, `attackModEnv=0` timecents, `delayModEnv=0` timecents. **Both timecents-zero fields correspond to 1.0 second, not instantaneous attack/delay.** The original reconstructed Creative converter maps attack to `ATKHLD=0x0C`. The relative MIDI note starts at 9.5s, the attack-analysis windows are 10.64–11.36s, followed by hold. Later hardware audio has been aligned only using P97's original coarse 0ms result; **no post hoc lag adjustment** in P205.
- The original physical source and reference files are pinned by Git blob SHA in `tests/fixtures/p205_eg1_ct4390_p200_points.json`. The fixture contains **only 10-row derived frequency metadata** from each prior P200 output, and 10 stable hold-bin medians; no audio, SF2, MIDI or ROM contents. Data contains nine matching *valid* native+hardware bins, one correctly rejected native/FFT ambiguity bin at 10.64s.
- Code: `tools/p205_eg1_domain_audit.py`. Run: `python tools/p205_eg1_domain_audit.py --self-test`; `python tools/p205_eg1_domain_audit.py --out p205-evidence/P205-EG1-CT4390-Domain-Audit.json`. Standard Python library only. Self-test intentionally mutates source run identity, physical bin, generator depth, and estimator validity to confirm guard detection.

## Physical inversion and a *limited* domain counterfactual

The original hardware note 59 stable hold pitch is **738.629 Hz**; baseline emulator stable hold pitch **740.183 Hz**, a stable **+3.64-cent** offset. We do **not** normalize away that offset in the primary metric. Original sustain at 523.829/523.379 Hz corroborates a lower EG1 modulation level; its phase is not treated as an attack measurement.

For the original `+1200-cent` pitch modulation, under the native current octave/cents interpretation and stable hold frequency `f_hold`, inferred normalized progress from the **native measured pitch** is:

```
x_native = 1 + log2(f_native / f_hold)             # progress 0..1
f0 = f_hold / 2
f_cents = f0 * 2**x_native                        # equals observed native pitch
f_hz_hypothetical = f0 * (1 + x_native)           # same progress, linear Hertz
```

Equivalently, changing from a **cent-linear** to a **Hertz-linear** mapping at the *same* latent progress changes the pitch displacement `1200*x` to `1200*log2(1+x)` cents. `log2(1+x) >= x` for `0 <= x <= 1`. It therefore *raises* intermediate pitches. The production/native waveform already rises too high/too early compared with the original CT4390; this particular remapping cannot by itself fix the failure. The independent original P200 native/hardware FFT/ACF acceptance masks, no phase-specific time alignment and no pitch/gain fits were retained.

| Attack over 9 accepted 80ms-spaced original bins | Median absolute pitch error | RMSE pitch error | Max absolute error |
|---|---:|---:|---:|
| Current 125A research baseline (actual native) | **81.85 cents** | **85.91 cents** | 118.97 cents |
| Counterfactual native progress reinterpreted as Hertz-linear (NOT rendered DSP) | **81.99 cents** | **94.13 cents** | 141.89 cents |
| P203 experimental slow-only **actual native** | 29.47 cents | 36.59 cents | 59.95 cents |

The reverse algebraic mapping (pretend the *already produced* native pitch had originally been Hertz-linear and reexpress it as cent-linear) reduces baseline RMSE, but this is not the algorithm currently used in the source (`snd_emu8k.c` routes the EG1 normalized value directly into fractional octaves/pitch increments). Reinterpreting the source as if it had a different original model does not establish the silicon behavior.

**This rejects only the simple cents→Hertz counterfactual on the existing envelope trajectory.** It does **not** reject Claude's general suggestion that the **internal** attack law might be derived from a different domain, a nonlinear conversion table, a different sample-phase clock or a revision-specific response. Those would require an explicit alternative implementation and independent validation on withheld rates/depths. One note 59 alone is not enough.

## New adversarial negative control: P203 attack is not monotone

The research-only P203 slow-rate formula (only when `ATKHLD < 0x10`) is:

```
y(x) = 1 - (1 - x)**13.5 - 0.30*x*(1-x)
```

It was tuned to reduce one note's median error. However, its derivative becomes **negative for normalized progress approximately 0.3206–0.4957** (1,751 negative adjacent steps in a 10,000-step mesh). The original `1-(1-x)^13.5` Block30 curve is monotonic. A *pitch-raising attack* therefore briefly falls in P203, **even though its median absolute reference error is lower**:

| P203 original note 59 | Actual measured pitch |
|---|---:|
| 10.88 s | 704.233 Hz |
| 10.96 s | 703.971 Hz |
| 11.04 s | 702.792 Hz |

The confirmed drop from 10.88 to 11.04 is **3.55 cents**; it is not an independently observed hardware behavior (physical CT4390 frequency rises through the same timestamps). These are FFT+ACF-consistent originally retained measurements, and the formula itself independently reproduces the negative derivative.

**Decision:** P203 is **falsified as a general slow-rate attack replacement** despite its 81.85→29.47-cent median improvement. Keep it research-only; do not merge it, do not overfit a compensating curve just to that one recording. No production DSP code modified in P205.

## Next independent tests with high information value

1. Audit the *actual original Creative* `ATKHLD`, `PEFE`, `IP` and live register histories for the reference EG1 note, including **relative-onset clock**, default modulators, note-on and readbacks. Hardware analog output can be unchanged while chip/driver state differs.
2. Test strictly monotone, predeclared domain hypotheses and at least two additional depths or rate codes, including `0x0C`, and **withhold** some original hardware examples from tuning. A result on note 59 alone does not certify other notes or preset banks.
3. If read-only original AWETST hardware captures for `0x0C` do not exist, state the gap. Do not falsely attribute its behavior to hardware-measured Block30 filter rates `0x10..0x3C`.
4. Maintain separation between source-ROM samples, mapped driver registers, EMU8000 internal DSP, analog card output and external capture chain. No original `Synth 512 Bank.sf2` specific physical recording currently exists.

**Gate:** The P205 pure-Python CI verifies the deterministic reanalysis and negative controls. It is **not** a new hardware measurement, full audit, release test, owner-SF2 test, ASIO test or VST3 validation. Product remains unchanged / release NO-GO.
