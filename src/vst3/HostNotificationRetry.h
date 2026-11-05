#pragma once
#include <cstdint>
namespace AWE125 {
// Track restartComponent failures without allowing an endless Win32 timer.
// Called only under the controller's UI-notification mutex.
class HostNotificationRetry {
public:
    static constexpr unsigned kMaxAttempts=3;
    bool ShouldRetry(uint64_t sequence,bool delivered) noexcept {
        if(sequence!=lastSequence_) {
            lastSequence_=sequence;
            attempts_=0;
        }
        if(delivered) {
            attempts_=0;
            return false;
        }
        return ++attempts_ < kMaxAttempts;
    }
private:
    uint64_t lastSequence_=0;
    unsigned attempts_=0;
};
} // namespace AWE125
