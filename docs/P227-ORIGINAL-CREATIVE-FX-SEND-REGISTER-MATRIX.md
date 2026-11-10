# P227 – genuine Creative Win95 FX CC91 / CC93 send-register sweep

Status: RESEARCH CANDIDATE, not a DSP or release fix. Test scope explicitly
distinct from owner-specific P226 original-bank sound acceptance.

## Why this test exists

P226 proved that the 125A VST3's actual 16-bit clipping is inherited
sample-for-sample from the emulated EMU8000's true signed32 output. Five wet
cases clip on the owner's original bank, four dry cases do not, and at full
GUI settings the VST3 writes 255 to each actual eight-bit send register.
Neither P226 nor 86Box's emulated output proves the original Creative Win95
MIDI/driver send coefficient equals 255 at any relevant MIDI CC91/93 value.

P89 (original Creative SBAWE.VXD with program000 "Grungy Ramp Bass",
note48, velocity100) measured an original chorus send byte 0x7F=127 in
CSL high. That is a separate earlier MIDI/CC condition, not one of the
current 16 private P226 clips. Do not substitute it for an exact
owner-bank 16-case comparison.

## Actual original driver path, unchanged and reused

- Proven P217 Win95 harness and guest disk staging in existing 86Box,
  original Windows95 Creative AWE64 Gold 28 MiB, original SBAWE.VXD and AWE
  Control Panel, WinMM Creative AWE endpoint and 86Box's own wavetable PCM.
- USB/VM/new sound engine NOT used. A disposable GitHub-hosted runner must
  reconstruct the previously proven ephemeral guest, like P217: that is not
  a permanently installed user's local virtual machine.
- Source SF2 authenticated by git blob 4768c4a0215abf49c7a2bb51ada5ba3494faa1c5
  (public original SoundFont Spec Test v3.0, 6 presets/25 instruments/44
  samples). This is NOT the user's 77-preset original Synth 512 Bank.sf2.
- Original SF2 sample-memory upload must be observed at voice26 AWE DRAM
  port after AWE Control Panel Apply; an inventory or GM fallback is not enough.
- P63 serial bridge carries 9 original WinMM messages per trial and P67
  verifies actual in-guest Creative endpoint, 144 delivery acknowledgements,
  original EMU8000 activity and audible wavetable PCM.

## 16 genuine Creative MIDI conditions

Use original public program 0 and 1, one supported note59; velocity64 or
120. Each program × velocity pair runs four stages:

| Stage | CC91 | CC93 |
|---|---:|---:|
| 0 | 0 | 0 |
| 1 | 127 | 0 |
| 2 | 0 | 127 |
| 3 | 127 | 127 |

Other CCs are constant: CC0=1 (Creative USER), CC7=100, CC11=127,
CC1=96. Each stage sends new program selection, note-on, one second hold,
note-off and an effect-tail pause. This is an ACTUAL original-driver
controller-response experiment; it intentionally changes CC91/93 between
stages because the historical Creative driver does not have our 125A
absolute 0-100% per-voice GUI override. Direct waveform/PCM identity
against P226 is **not** claimed and would be invalid across different SF2s.

For each real WinMM note window record the original EMU8000 ISA port-write
values (not a predicted formula): high byte of PTRX_LO = 8-bit reverb send,
high byte of CSL_HI = 8-bit chorus send; require a real PSST sample-start
voice and matching send writes. Preserve multiple real voices and
per-voice write histories; never accept the voice26 DRAM-upload channel as
a note. Capture the genuine 86Box wavetable output to transient WAV,
measure 44,100 Hz stereo PCM16 peak, RMS, DC, rails and nonzero frames,
and publish only numerical summaries/sha256, not ROMs, drivers, Win95
guest, original media or WAV.

## Source and test-quality gates

- The original P217 staging workflow is reused in a separate private
  engineering-branch workflow. No VST3 output, FX algorithm or audio file
  is altered.
- Python P227 command matrix and actual-register decoder have four
  deliberately wrong-register/voice negative controls. Separate P227
  evidence validator checks original guest proof, source git hash,
  16 identity/CC/velocity cases, nonoverlapping port-write windows,
  voice and send register values, real nonzero wavetable PCM and
  prevention of invented P226 parity claims.
- If no authentic Creative CC-driven register change is observed, report
  that as a **measured non-response**, not as a guessed curve.
- End-to-end P227 has to finish the actual original Win95/86Box workflow
  and produce source-verified JSON for a meaningful completion claim.

## Boundaries

The sampled source program and note differ from the user's original
bank and P226's note48/note72 cases; P227 can establish how the genuine
Win95 driver responds to tested CC91/CC93 and the actual sent register
bytes in that setup, not solve sound parity for user SF2 programs P000
and P021. To call P226's historic gain law correct or incorrect for the
user bank, re-run the original Creative Win95 driver with that EXACT bank,
selected program, note, velocity, user-bank CC, and instrument/effect
presets, then compare original register sends and physical/emulated audio
with calibrated levels. Physical AWE64/ASIO still NOT RUN.

No arbitrary reverb/chorus gain, DC removal, limiter or GUI send-taper
change is authorized by this research candidate.
