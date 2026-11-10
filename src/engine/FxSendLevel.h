#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// P223: the visible send knob controls the *actual eight-bit EMU8000
// voice-send hardware register* directly. This is a transparent hardware
// register mapping (0% -> 0, 100% -> 255), not an invented nonlinear
// enrichment/boost curve tied to the SoundFont patch value.
//
// The original Creative SF2/CC91/CC93 send calculation is still performed
// upstream and preserved in Synth::VoiceAlloc for hardware/driver oracles.
// The 125A 0%=dry GUI contract explicitly overrides that original send.
// Consequently this GUI is a user override, NOT a historical Creative driver
// front-panel control. Original-driver comparisons MUST use captured hardware
// register values rather than assuming equal GUI percentages imply parity.
namespace AWE125::FxSendLevel {
inline std::uint8_t Apply(int /*creativeSend*/, float amount) noexcept {
    if (!std::isfinite(amount) || amount <= 0.f) return 0;
    const double x = std::clamp(static_cast<double>(amount), 0., 1.);
    return static_cast<std::uint8_t>(
        std::clamp(std::lround(255.0 * x), 0L, 255L));
}
}
