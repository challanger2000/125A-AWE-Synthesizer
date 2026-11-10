#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// P223: preserve the Creative driver / SoundFont / MIDI per-voice send.
// This is a user-facing ATTENUATOR of the existing EMU8000 send register,
// not a substitute for the Creative CC91/CC93 calculation.
// 0 -> hardware send 0 (dry); 1 -> exactly the original hardware send.
// No user knob position is allowed to amplify the driver's send.
// This is a modern 125A bypass/attenuation control, NOT a claim that
// Creative shipped an equivalent continuous hardware GUI knob.
namespace AWE125::FxSendLevel {
inline std::uint8_t Apply(int sf2AndMidiSend, float amount) noexcept {
    if (!std::isfinite(amount) || amount <= 0.f) return 0;
    const double x = std::clamp(static_cast<double>(amount), 0., 1.);
    const double base = std::clamp(static_cast<double>(sf2AndMidiSend), 0., 255.);
    return static_cast<std::uint8_t>(
        std::clamp(std::lround(base * x), 0L, 255L));
}
}
