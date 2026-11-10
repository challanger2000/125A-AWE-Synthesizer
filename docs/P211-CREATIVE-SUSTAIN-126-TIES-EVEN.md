> **SUPERSEDED / FALSIFIED by P212 (2026-11-10).** The P211 126-scale ties-to-even model matched the seven distinct P210 Sustain settings but only 22/28 new P212 original-driver cases. Do not merge it. Later hash-verified original `SBAWE.VXD` analysis identified signed integer arithmetic; when the separately converted instrument-500 and additive preset-delta fixture stages are respected, 42/42 independently measured Creative register cases match. See [P213 finding](P213-SUSTAIN-SOURCE-DERIVED-FINDING.md) and [successful P213 audit](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42734359204). General SF2 layer call graph and hardware parity remain unverified; no production DSP change.

---

# P211 – Original Creative EG1 SF2 Sustain: distinct-scale hypothesis

Only 14 genuine Creative Windows 95 register examples from [P210](https://github.com/challanger2000/125A-Engineering/actions/runs/42722686808) are reused; 7 distinct SustainModEnv generator values. Source bank was the authenticated original public SoundFont Spec Test v3.0 with unchanged instrument sample and 14 appended preset-only variants. Native chip and product DSP NOT changed here.

The old 125A modulation sustain conversion scaled by 127 and used lround: 3/14 P210 cases. The research P208 candidate also scaled by 127 but truncated: 11/14. Observed exceptions:

- SF2 250: original high-byte 0x5F; P208 0x60
- SF2 750: original 0x21; P208 0x20
- SF2 1000: original 0x01; P208 0x00

Independent P211 prediction is **127 - round_ties_to_even(126 * amount / 1000)**. This matches all 14 archived driver cases, including 250, 750 and 1000. A 126-scale / round-half-up model differs at an exactly-half case, therefore tie handling is evidence-based, not arbitrary. Six intentionally corrupted source controls must fail.

**Critical:** 14 matches across only 7 distinct input values do not prove general mapping. P211 does not run the original Creative driver again, does not execute physical EMU8000 silicon and does not change the shipping VST3. Additional withheld values and the actual SBAWE.VXD conversion routine are required before promoting any formula. Chip attack pitch mismatch 81.85 cents unresolved. CI success = mathematical evidence audit only, not original hardware fidelity, DAW/ASIO, full audit or release.
