#pragma once
#include <algorithm>
#include <cstdint>

namespace AWE125 {
// SBAWE.VXD uses a deferred pan step every 227 *native* EMU8000 frames.
// Convert that period to host frames with carried fractional error so 48/96
// kHz do not change the glide speed or accumulate rounding drift.
struct VxdPanClock {
    static constexpr uint32_t kNativeRate = 44100;
    static constexpr uint32_t kNativeFramesPerStep = 227;
    static constexpr uint32_t kInitialRemainder = kNativeRate / 2;
    static uint32_t NextHostFrames(uint32_t hostRate,
                                   uint32_t& remainder) noexcept {
        const uint64_t ticks =
            uint64_t{kNativeFramesPerStep} * std::max(hostRate, 1u)
            + remainder;
        remainder = static_cast<uint32_t>(ticks % kNativeRate);
        return std::max<uint32_t>(1,static_cast<uint32_t>(ticks / kNativeRate));
    }
};
} // namespace AWE125
