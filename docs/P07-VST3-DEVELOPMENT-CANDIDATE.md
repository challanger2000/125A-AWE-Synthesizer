# P07 — experimental VST3 processor/controller

SDK: Steinberg VST3 3.8.1, tag `v3.8.1_build_84` at
`3cdf9ca5d1f5b1b21e0a86832aa4abe55607bd96`.

A separate AudioEffect processor and EditControllerEx1 class expose
stereo output, one MIDI event input, a 128-program host parameter and
versioned state for Program. VST3 NoteOn/NoteOff are split at host sample
offsets into native Synth::RenderBlock. The float output is converted from
the preallocated interleaved int16 render scratch (kSample32 only).

Development-only external asset startup: AWE32_ROM_PATH and
AWE32_SF2_PATH environment variables. No ROM or SF2 is included.
The paths are consulted only from setActive; absent or invalid assets
currently fall back to the native-model synthetic oscillator. This is
not a user-facing asset workflow.

No custom GUI, no sample-accurate Program automation, no MIDI CC mapping,
no project-managed SF2/ROM paths, no Steinberg Validator or Studio One
signoff. This is a Windows SDK build candidate only.

## Steinberg Validator issues identified in initial build

Initial candidate successfully compiled into a Windows x64 VST3 bundle
but failed 6 of 47 validator checks (run #41233360306):
- three valid parameter flushes without audio buffers,
- mono output and two altered bus/automation arrangements.
The test also warned on setupProcessing at non-audio test rates 1234.568
and 1234567.8 Hz. This patch processes parameter-only calls before
examining audio buffers, supports mono downmix and accepts positive finite
host probe rates safely. The SDK post-build validator remains the gate;
new build evidence must confirm whether all findings are actually fixed.

Windows developer artifacts are generated only after a successful build and
validator run; ROM/SF2 contents are excluded.

## Source-contract false-positive, test adequacy and repair

The first actual Windows VST3 module built successfully and the Steinberg
Validator passed **47/47** in run #41233625685. The workflow was not green
because `125A_source_baseline_contract` incorrectly flagged
`external/vst3sdk/public.sdk/samples/vst/again_auv3/Shared/drumLoop.wav`
from the freshly cloned Steinberg SDK. That is SDK-owned example content,
not an asset checked into 125A. The source-contract check now excludes **only**
this exact Steinberg SDK clone root while continuing to reject protected
ROM/SF2/WAV assets under every other project directory. This is not a
validator workaround and leaves the audio-content prohibition intact.

A separate processor issue found during review: the VST3 host can flush
Program changes before `setActive`; previous code dereferenced a null
`synth_`. The corrected path retains Program state and applies it when
activation creates the synthesizer.

Status of these changes requires a matching successful CI run; no user
asset/Studio One parity claim is implied.

## P07.1 ROM-free VST3 packaging
The first artifact passed Steinberg Validator 47/47 but the SDK-generated
`moduleinfo.json` contained trailing commas, rejected by a strict JSON parser.
A dedicated post-validation packaging gate now strips only unquoted trailing
commas and independently parses the resulting JSON. It preserves all class
IDs, names and metadata. The artifact now includes the outer
`125A_AWE_Synthesizer.vst3` directory for direct installation.
Build and test results for this packaging commit must be verified separately.
