#pragma once
// Exclusive 86Box-hardware mode for the Windows AWE64 VST3.
// A configured and successfully loaded SF2 is not sufficient: 86Box must
// actually have started from a validated original EMU8000 wave ROM.
// The pure-native Synth used by independent engine tests is unaffected.
namespace AWE125 {
constexpr bool AllowEmuNoteOn(bool sf2Configured,bool sf2Loaded,
                               bool romBacked86BoxActive) noexcept {
    return sf2Configured && sf2Loaded && romBacked86BoxActive;
}
} // namespace AWE125
