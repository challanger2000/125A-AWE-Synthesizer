# P198 – Win95 SF2 attenuation factor: physical AWE64 Gold calibration

Date: 2026-11-09. Product branch `fix/p190-zero-fx-dry`.
Target: Win95 / SF2 `initialAttenuation` only. P190 absolute 0%-FX-dry,
EMU8000 source, ROM, GUI, state, and the legacy DOS/SDK/SF1 converters
must remain unchanged.

## Hardware source and independent controls

The same SHA-pinned [SoundFont Spec Test v3.0](https://github.com/mrbumpy409/SoundFont-Spec-Test)
MIDI, SoundFont, and real analog AWE64 Gold CT4390 FLAC were used for every
trial. P197 inspected the **actual RIFF generators**: notes 65,66,67,68,69
all play **sampleID=43**, set their `overridingRootKey` equal to the MIDI note
(thus identical base pitch) and have initial attenuation 100,150,200,250,300
centibels. They use the same original 420ms note duration and velocity 127.

The comparison computes relative losses with the *same single global P97 gain*
(no per-note normalization). Six independent time slices across each note
confirmed the P104 mismatch before any retuning: native minus hardware
-0.548 (onset), -0.569 (early), -0.556 (middle), -0.556 (late),
-0.569 dB/5-SF2-dB (pre-release). It is **not** simply an inaccurate
attack/hold envelope or varying sample/pitch. The 0.40 conversion was
already preferable to unconverted SF2 1.0, but still measurably off.

## Mutually isolated research variants

[P198 full dual-candidate CI run #42592479485](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42592479485),
both 264-second 86Box renders **SUCCESS**. The `AWE125_P198_ATTEN_SCALE`
flag exists **only in the separate research branch**, is explicitly
restricted to 0.50/0.53 and cannot be used with VST3 or without the
nonshipping P193 physical-reference mode.

| Scale | Mean hardware loss per 5 SF2 dB | Native | Delta | Intermediate-step fidelity |
|---|---:|---:|---:|---|
| P104 baseline 0.40 | 2.258 dB | 1.700 dB | -0.558 dB | Too little attenuation |
| **P198 candidate 0.50** | **2.258 dB** | **2.267 dB** | **+0.008 dB** | Note-relative middle/late errors **0.00..+0.042 dB** |
| P198 candidate 0.53 | 2.258 dB | 2.267 dB | +0.008 dB | Intermediate notes **+0.77..+1.17 dB error** |

**Why the numerical average alone is invalid:** IFATN is quantized in 0.375dB
steps. Both 0.50 and 0.53 happened to yield the same endpoint difference
because they quantized the 100/300cB endpoints to equivalent effective
attenuations. However, 0.53 attenuated the 150/200/250cB intermediate
steps too strongly. The individually matched notes select **0.50**.

The 0.50 result was consistent across onset/early/middle/late/pre-off
windows: native minus hardware step error +0.019, -0.002, +0.010,
+0.010, -0.002 dB respectively. Post-note-off tails still differ and
cannot be used as evidence for a register-conversion change.

## Change and QA scope

Production `SoundFont::MakeVoiceParams` Win95 SF2 attenuation factor
`0.40 -> 0.50`, with no source-dependent conditional or per-bank fitting.
The registered P90 driver-converter regression now verifies 0/50/100/150/
200/250/300 cB quantization at 0.50 for Win95 and retains legacy 1.0 for DOS.
Other measured original Creative pitch/FX/filter/ADSR register vectors remain.

**Evidence:** The native P198 hardware experiment is green. The promoted
Windows VST3 and full CTest/Steinberg validator/Test Lab/RT matrix must be
run **again on the exact production P198 commit**. A previous P196 Windows
PASS may not be reused as acceptance for this changed source.

**Limits:** This is a quantitatively supported match to a publicly
captured analog AWE64 reference, **not** a recovered exact original Win95
VXD formula, silicon-exact PCM, or all-SF2 authorization. Physical real
ASIO/Studio Pro owner acceptance and an independent FULL AUDIT remain OPEN;
commercial release remains NO-GO.
