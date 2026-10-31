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
