## Verifiziertes Original-Creative-Ergebnis (10. November 2026)

[**P214 Originaltreiber GitHub Actions #42737751948: SUCCESS**](https://github.com/challanger2000/125A-Engineering/actions/runs/42737751948), Artefakt `P214-Creative-Win95-EG1-28Program-InstrumentBase-Register-Oracle` (GitHub-Artefakt-ID `13727998644`). Die Originaltreiber-Messung bestand aus 28 isolierten, geordneten Noten-/Registerfenstern für die authentifizierte, ausschließlich ergänzte SF2-Bank. Die kontrollierte zweistufige Sustain-Berechnung traf **28/28** Creative-Registerwerte, davon **21/21** bei neuen Instrument-Grundwerten (0, 250, 1000) und **7/7** historische Kontrollen bei Basis 500. Der GitHub-Test prüfte originale MIDI/WinMM-Übertragung, Audiosignal und die Herkunft der SF2-Daten.

**Grenzen:** Nur die geprüften Sustain-Kombinationen im emulierten 86Box/Win95-Originaltreiber sind belegt; Original-Silizium, unabhängige Hardware-Klangmessung, andere SF2-Generator-Kombinationen, kompletter Aufrufpfad und Studio-One-ASIO-Abnahme sind weiterhin offen. Kein DSP-Patch und keine Releasefreigabe. Der frühere abgebrochene Installationslauf #42735984635 ist kein Messergebnis.

---

# P214 – Independent original Creative instrument-base × preset Sustain experiment

**Research only; source driver verification does not equal release certification.**

## Question

P213's source-derived calculation `T(500)+T(sustain-500)-127` reproduces all 42 historical register cases, but **every one** used the same underlying SoundFont instrument `sustainModEnv=500`. A coincidental formula could still pass these measurements. We must vary the instrument and the preset **independently**, while preserving the authenticated original sample and every preexisting source instrument.

## Frozen matrix and source

- Authenticated, Creative-accepted public SoundFont Spec Test v3.0: Git blob `4768c4a0215abf49c7a2bb51ada5ba3494faa1c5`; SoundFont source version, inventory and sample43/note59 source semantics are verified before modification.
- Original instrument Sustain base values: **0, 250, 500, 1000**.
- Final requested Sustain values for each base: **0, 1, 249, 250, 500, 750, 1000**.
- Appended programs: **100 through 127**, 28 distinct `(instrument base, preset delta)` pairs.
- Instrument-base 500 uses the **original unmodified instrument**: 7 direct control cases from P210/P212. The other 21 use three new *clones* of the original target instrument, with only Sustain generator 29 changed to the base value. Preset generator 29 adds `requested - base`, and preset generator 41 selects the correct clone.
- All **six original presets, 25 original instrument records and original modulator/generator zones, 44 sample records, and the source INFO/SDTA audio bytes** are preserved byte-for-byte. Only appended instrument/preset structures change.
- MIDI note 59, velocity 100, Creative User Bank 1, program 100..127. Original Creative `SBAWE.VXD` (SHA-256 `d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a`) under Windows 95 and 86Box AWE64 Gold.

## Falsifiable source-derived hypothesis

`T(x) = 127 + trunc_towards_zero((-127 * x) / 1000)`

`predicted = clamp_0_127(T(base) + T(requested - base) - 127)`

The P214 comparison evaluates that candidate **after** capturing fresh original Creative DCYSUS register values. It also records direct `T(requested)` for contrast.

Independent original-driver notes must exhibit exactly one active voice and the expected modulation envelope write pattern. Seven base-500 original repeat controls must equal P210/P212, or the source observation is rejected. Other programme paths (delay/pitch envelope) must stay equal, preventing silent fallback from being counted as Sustain evidence. The 21 new-base predictions may mismatch; CI must preserve those mismatches and must **not** invent expected Creative values.

## Test adequacy / known boundaries

| Required evidence | Source | Acceptance | Status |
| --- | --- | --- | --- |
| Authenticated original SF2 and immutable 44 sample records | `p214_clone_instrument_matrix.py` | SHA-1 source ID, unchanged original tables/audio and rigorous matrix verification | Pending full CI execution |
| 28 genuine Windows 95 Creative windows | `p48_86box_boot_win95.py` with `--p214-sweep` | Original WinMM/COM1, verified ROM/sample upload/PCM, ordered windows | Pending full CI execution |
| Genuine Creative register output | `p214_compare_creative_instrument_base.py` | One voice, exact ATKHLD/DCYSUS counts, seven historically observed controls | Pending full CI execution |
| Formula versus original driver | Same comparator | Independent match count for 21 previously untested bases, no self-fulfilling oracle | Pending full CI execution |
| Malformed provenance/fixture controls | Comparator and generator self-tests | Fail closed on 9 comparator and 4 source-matrix mutations | Test logic added, independent CI preflight required |
| Physical original AWE64 silicon and Windows Studio One ASIO | Hardware / DAW | Original target physical-audio / VST3 host acceptance | **NOT RUN** |

## CI runner reliability note

Original workflow [#42735984635](https://github.com/challanger2000/125A-Engineering/actions/runs/42735984635) was cancelled due an unusually stalled dependency-installation step; **that first run produced no new original Creative measurements**. The replacement workflow [#42737751948](https://github.com/challanger2000/125A-Engineering/actions/runs/42737751948) generates and verifies the bank before expensive tool installation, uses bounded apt-update/install timeouts and is the only P214 original-driver run relevant to new empirical results. The independent, inexpensive bank preflight [#42736933567](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42736933567) already passed.

## Links

- [P214 original Creative test workflow](https://github.com/challanger2000/125A-Engineering/actions/runs/42737751948).
- [P213 verified VxD source-derived findings](P213-SUSTAIN-SOURCE-DERIVED-FINDING.md).
- [P212 genuine original-driver result](https://github.com/challanger2000/125A-Engineering/actions/runs/42727927825).

**Release gate: NO-GO.** No changes to product DSP, GUI, automation, state, ROM processing, or shipping VST3.
