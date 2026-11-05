#pragma once
#include <atomic>
#include <cstdint>

namespace AWE125 {
// Bank decisions have three independent producers:
//   - completed project recall (control, serialized by engineMutex_)
//   - browser messages (possibly competing host/control threads)
//   - host bank-parameter edits (single realtime process thread)
// A global bank decision never consumes a channel-local MIDI CC0/32 event.
// The monotonically assigned stamp defines intent order. In particular, a
// recall's stamp is allocated BEFORE its slow IBStream read/asset preparation.
//
// The realtime producer makes one atomic fetch_add and one atomic store, never
// an allocation, lock, spin or control-thread callback. Only the non-RT
// browser producer needs a CAS retry to preserve stamp order.
class BankOrder {
public:
    struct Choice {
        uint64_t sequence=0;
        uint16_t bank=0;
    };
    uint64_t Next() noexcept {
        return next_.fetch_add(1,std::memory_order_acq_rel);
    }
    uint64_t BeginRecall() noexcept { return Next(); }
    void CommitRecall(uint64_t sequence,uint16_t bank) noexcept {
        // Callers serialize successful recalls with engineMutex_ and reject
        // a stale assetGeneration_ before publishing.
        recall_.store(Pack(sequence,bank),std::memory_order_release);
    }
    uint64_t PublishAudio(uint16_t bank) noexcept {
        const uint64_t sequence=Next();
        audio_.store(Pack(sequence,bank),std::memory_order_release);
        return sequence;
    }
    void PublishBrowser(uint16_t bank) noexcept {
        const uint64_t desired=Pack(Next(),bank);
        uint64_t before=browser_.load(std::memory_order_acquire);
        while(Sequence(before)<Sequence(desired) &&
              !browser_.compare_exchange_weak(before,desired,
                  std::memory_order_acq_rel,std::memory_order_acquire)) {
            // UI/host thread only. An older, delayed publisher can never
            // overwrite a more recent accepted bank.
        }
    }
    Choice Latest() const noexcept {
        uint64_t latest=recall_.load(std::memory_order_acquire);
        const uint64_t ui=browser_.load(std::memory_order_acquire);
        if(Sequence(ui)>Sequence(latest))latest=ui;
        const uint64_t rt=audio_.load(std::memory_order_acquire);
        if(Sequence(rt)>Sequence(latest))latest=rt;
        return Decode(latest);
    }
    Choice LatestRecall() const noexcept {
        return Decode(recall_.load(std::memory_order_acquire));
    }
private:
    static uint64_t Pack(uint64_t sequence,uint16_t bank) noexcept {
        return (sequence<<16)|bank;
    }
    static uint64_t Sequence(uint64_t packed) noexcept {
        return packed>>16;
    }
    static Choice Decode(uint64_t packed) noexcept {
        return {Sequence(packed),static_cast<uint16_t>(packed&0xFFFFu)};
    }
    std::atomic<uint64_t> next_{1};
    std::atomic<uint64_t> browser_{0},audio_{0},recall_{0};
};
} // namespace AWE125
