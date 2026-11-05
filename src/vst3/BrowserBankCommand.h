#pragma once
#include <atomic>
#include <cstdint>

namespace AWE125 {
// UI/connection thread -> audio thread: a nonallocating one-shot bank command.
// The upper bits encode an increasing generation so repeated selections of
// the same bank remain distinguishable. Both fields publish atomically.
class BrowserBankCommand {
public:
    bool Publish(unsigned bank) noexcept {
        if(bank>16383u)return false;
        uint64_t previous=packed_.load(std::memory_order_relaxed);
        for(;;) {
            const uint64_t next=((previous+(uint64_t{1}<<16))&
                                ~uint64_t{0xFFFF})|bank;
            if(packed_.compare_exchange_weak(previous,next,
                    std::memory_order_release,std::memory_order_relaxed))
                return true;
        }
    }
    // Snapshot at the START of a (possibly slow) project recall. A later
    // accepted browser selection must not be overwritten by the old recall.
    uint64_t Snapshot() const noexcept {
        return packed_.load(std::memory_order_acquire);
    }
    bool HasPending(uint64_t last) const noexcept {
        const uint64_t now=Snapshot();
        return now!=0 && now!=last;
    }
    // Control-thread recall may replace only the command that existed when
    // the recall STARTED. On failure, expected becomes the newer accepted
    // command, allowing its bank to win the state publication.
    bool PublishRecallIfUnchanged(uint64_t& expected,unsigned bank) noexcept {
        if(bank>16383u)return false;
        const uint64_t next=((expected+(uint64_t{1}<<16))&
                              ~uint64_t{0xFFFF})|bank;
        return packed_.compare_exchange_strong(
            expected,next,std::memory_order_acq_rel,
            std::memory_order_acquire);
    }
    bool Consume(uint64_t& last,uint16_t& bank) const noexcept {
        const uint64_t state=packed_.load(std::memory_order_acquire);
        if(state==0||state==last)return false;
        bank=static_cast<uint16_t>(state&0xFFFFu);
        last=state;
        return true;
    }
private:
    std::atomic<uint64_t> packed_{0};
};
} // namespace AWE125
