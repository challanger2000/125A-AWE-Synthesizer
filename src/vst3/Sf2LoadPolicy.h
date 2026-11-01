#pragma once
// P20: do not present the synthetic default sine as the requested SoundFont
// when an explicit SF2 path failed to load. No file access in audio callback.
namespace AWE125 {
constexpr bool AllowEmuNoteOn(bool sf2Configured,bool sf2Loaded) noexcept {
    return !sf2Configured || sf2Loaded;
}
} // namespace AWE125
