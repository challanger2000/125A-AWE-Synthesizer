#pragma once
#include <algorithm>
#include <cstdint>

namespace AWE125::MasterOutput {

// Independent of the 12 SF2 enhancement knobs (1100-1111).
// The master volume is post-chip only: 100% is exactly unity, 0% is mute.
inline constexpr uint32_t kParamID=1003;
inline constexpr uint32_t kScale=10000u;
inline constexpr uint32_t kDefault=kScale;

// A fixed 64-output-frame linear ramp avoids zipper jumps. A note keeps
// progressing inside the EMU8000 while muted; changing the master cannot
// affect chip register writes, velocity, envelopes, bank loading or ROM.
class Gain {
public:
    float current() const noexcept {return current_;}
    float target() const noexcept {return target_;}
    void restore(uint32_t stored) noexcept {
        current_=target_=fromStored(stored);
        step_=0.f;
        remaining_=0;
    }
    void setTarget(uint32_t stored) noexcept {
        const float next=fromStored(stored);
        if(next==target_)return;
        target_=next;
        remaining_=64;
        step_=(target_-current_)/64.f;
    }
    float next() noexcept {
        if(remaining_>0) {
            --remaining_;
            current_ = remaining_ ? current_+step_ : target_;
        }
        return current_;
    }
    static float fromStored(uint32_t value) noexcept {
        return static_cast<float>(std::min(value,kScale))/static_cast<float>(kScale);
    }
private:
    float current_=1.f,target_=1.f,step_=0.f;
    int remaining_=0;
};
} // namespace AWE125::MasterOutput
