#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// P190: global user-visible send level (0..1). The original SF2/CC send
// determines the midpoint curve, but can NEVER override an explicit zero.
// 0 -> dry (0 on both EMU8000 effect buses); 1 -> hardware send 255.
// This is not the discrete Creative chorus/reverb PRESET index.
namespace AWE125::FxSendLevel {
inline std::uint8_t Apply(int sf2AndMidiSend, float amount) noexcept {
    if (!std::isfinite(amount) || amount <= 0.f) return 0;
    const double x = std::clamp(static_cast<double>(amount), 0., 1.);
    const double base = std::clamp(static_cast<double>(sf2AndMidiSend), 0., 255.);
    const double send = x * (base + (255. - base) * x);
    return static_cast<std::uint8_t>(std::clamp(std::lround(send),0L,255L));
}
}
